"""Pipeline de ingestão, geração resiliente de embeddings e indexação HNSW no pgvector."""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.db.session import get_db_session
from lumi.db.vector_store import NormativeVectorStore
from lumi.ingestion.chunker import chunk_document
from lumi.ingestion.parser import parse_document
from lumi.rag.llm_factory import get_embeddings

logger = structlog.get_logger(__name__)


class IngestionResult(BaseModel):
    """Métricas e resultado da ingestão e indexação vetorial de um documento normativo."""

    model_config = ConfigDict(frozen=True)

    document_code: str = Field(description="Código identificador da norma (ex.: 'DIS-NOR-030')")
    revision: str = Field(description="Versão ou revisão da norma (ex.: '07' ou 'REV07')")
    total_chunks: int = Field(ge=0, description="Quantidade total de chunks indexados no banco")
    duration_seconds: float = Field(ge=0.0, description="Tempo total de execução em segundos")
    status: str = Field(description="Status final do processo ('success' ou 'error')")
    error_message: str | None = Field(
        default=None,
        description="Mensagem de erro em caso de falha no pipeline",
    )


async def generate_embeddings_with_retry(
    texts: list[str],
    provider: str | None = None,
    batch_size: int = 32,
    max_retries: int = 3,
    retry_backoffs: tuple[float, ...] = (1.0, 2.0, 4.0),
    batch_delay: float = 0.2,
    embedding_service: Any = None,
) -> list[list[float]]:
    """Gera embeddings em lotes com rate limiting defensivo e retentativas com backoff exponencial.

    Args:
        texts: Lista de conteúdos textuais a serem vetorizados.
        provider: Nome do provedor de embeddings ("gemini" ou "fake").
        batch_size: Quantidade de fragmentos por requisição ao provedor.
        max_retries: Número máximo de tentativas por lote em caso de falha transitória / 429.
        retry_backoffs: Delays de espera em segundos para cada tentativa.
        batch_delay: Intervalo defensivo de respiro em segundos entre lotes subsequentes.
        embedding_service: Serviço de embeddings opcional (injetável para testes).

    Returns:
        list[list[float]]: Lista sequencial de vetores de embedding gerados.
    """
    if not texts:
        return []

    service = embedding_service or get_embeddings(provider=provider)
    all_embeddings: list[list[float]] = []
    total_texts = len(texts)

    for i in range(0, total_texts, batch_size):
        batch = texts[i : i + batch_size]
        batch_index = (i // batch_size) + 1
        total_batches = (total_texts + batch_size - 1) // batch_size

        batch_vectors: list[list[float]] | None = None

        for attempt in range(max_retries):
            try:
                if hasattr(service, "aembed_documents"):
                    batch_vectors = await service.aembed_documents(batch)
                else:
                    batch_vectors = service.embed_documents(batch)
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    logger.error(
                        "Falha ao gerar embeddings após todas as retentativas",
                        batch_index=batch_index,
                        total_batches=total_batches,
                        error=str(exc),
                    )
                    raise
                backoff = (
                    retry_backoffs[attempt] if attempt < len(retry_backoffs) else retry_backoffs[-1]
                )
                logger.warning(
                    "Falha temporária ao gerar embeddings; retentando...",
                    batch_index=batch_index,
                    attempt=attempt + 1,
                    backoff_seconds=backoff,
                    error=str(exc),
                )
                await asyncio.sleep(backoff)

        if batch_vectors is not None:
            all_embeddings.extend(batch_vectors)

        # Rate limiting defensivo entre lotes (não aguarda após o último lote)
        if i + batch_size < total_texts and batch_delay > 0:
            await asyncio.sleep(batch_delay)

    return all_embeddings


async def ingest_normative_file(
    file_path: Path | str,
    provider: str | None = None,
    batch_size: int = 32,
    session: AsyncSession | None = None,
    raise_on_error: bool = False,
) -> IngestionResult:
    """Orquestra o ciclo completo de ingestão, chunking, geração de embeddings e persistência.

    1. Realiza parsing do documento técnico (Markdown ou PDF).
    2. Executa chunking semântico híbrido orientado a seções e tabelas.
    3. Gera tensores de embedding em lotes com tratamento defensivo de falhas.
    4. Persiste no PostgreSQL com índice HNSW via NormativeVectorStore com idempotência estrita.
    5. Retorna relatório estruturado com métricas de execução.

    Args:
        file_path: Caminho para o arquivo normativo (.md ou .pdf).
        provider: Provedor de embeddings ("gemini" ou "fake").
        batch_size: Tamanho do lote para vetorização.
        session: Sessão SQLAlchemy assíncrona opcional (se None, utiliza get_db_session).
        raise_on_error: Se True, propaga exceções em vez de encapsular em IngestionResult.

    Returns:
        IngestionResult: Resultado com código, revisão, contagem de chunks e duração.
    """
    start_time = time.perf_counter()
    path = Path(file_path)

    try:
        # 1. Parsing estruturado do documento
        parsed_doc = parse_document(path)

        # 2. Chunking híbrido semântico
        chunks = chunk_document(parsed_doc)
        if not chunks:
            duration = time.perf_counter() - start_time
            return IngestionResult(
                document_code=parsed_doc.document_code,
                revision=parsed_doc.revision,
                total_chunks=0,
                duration_seconds=round(duration, 3),
                status="success",
            )

        # 3. Geração em lotes de embeddings vetoriais
        texts = [chunk.content for chunk in chunks]
        embeddings = await generate_embeddings_with_retry(
            texts=texts,
            provider=provider,
            batch_size=batch_size,
        )

        # 4. Persistência transacional e idempotente via NormativeVectorStore
        async def _persist(s: AsyncSession) -> int:
            store = NormativeVectorStore(s)
            return await store.upsert_document_with_chunks(
                document_code=parsed_doc.document_code,
                title=parsed_doc.title,
                revision=parsed_doc.revision,
                chunks_data=chunks,
                embeddings=embeddings,
            )

        if session is not None:
            total_chunks = await _persist(session)
        else:
            async with get_db_session() as s:
                total_chunks = await _persist(s)

        duration = time.perf_counter() - start_time
        logger.info(
            "Documento normativo indexado com sucesso",
            document_code=parsed_doc.document_code,
            revision=parsed_doc.revision,
            total_chunks=total_chunks,
            duration_seconds=round(duration, 3),
        )

        return IngestionResult(
            document_code=parsed_doc.document_code,
            revision=parsed_doc.revision,
            total_chunks=total_chunks,
            duration_seconds=round(duration, 3),
            status="success",
        )

    except Exception as exc:
        if raise_on_error:
            raise
        duration = time.perf_counter() - start_time
        doc_code = getattr(locals().get("parsed_doc"), "document_code", path.stem)
        rev = getattr(locals().get("parsed_doc"), "revision", "UNKNOWN")
        logger.error(
            "Erro durante a ingestão do documento normativo",
            file_path=str(path),
            error=str(exc),
        )
        return IngestionResult(
            document_code=doc_code,
            revision=rev,
            total_chunks=0,
            duration_seconds=round(duration, 3),
            status="error",
            error_message=str(exc),
        )


def _build_argument_parser() -> argparse.ArgumentParser:
    """Cria e configura o parser de linha de comando para a ingestão normativa."""
    parser = argparse.ArgumentParser(
        prog="python -m lumi.ingestion.pipeline",
        description=(
            "Pipeline de ingestão, vetorização e indexação de normas técnicas "
            "com persistência pgvector HNSW no Lumi NeoGuide."
        ),
    )
    parser.add_argument(
        "path",
        type=str,
        help="Caminho para o arquivo normativo (.md, .pdf) ou diretório.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["gemini", "fake"],
        default=None,
        help="Provedor de embeddings ('gemini' ou 'fake'). Padrão derivado das configurações.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Quantidade de chunks por lote na geração de embeddings (padrão: 32).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Varre e processa recursivamente todos os arquivos normativos (.md, .pdf) no diretório informado.",
    )
    return parser


async def main(args: list[str] | None = None) -> int:
    """Ponto de entrada assíncrono para execução via CLI."""
    parser = _build_argument_parser()
    cli_args = parser.parse_args(args)

    target_path = Path(cli_args.path)
    if not target_path.exists():
        print(f"Erro: Caminho especificado não existe: {target_path}", file=sys.stderr)
        return 1

    files_to_process: list[Path] = []
    if cli_args.all or target_path.is_dir():
        if target_path.is_dir():
            md_files = list(target_path.glob("**/*.md"))
            pdf_files = list(target_path.glob("**/*.pdf"))
            files_to_process = sorted(md_files + pdf_files)
        else:
            files_to_process = [target_path]
    else:
        files_to_process = [target_path]

    if not files_to_process:
        print(
            f"Nenhum arquivo normativo (.md ou .pdf) localizado em: {target_path}",
            file=sys.stderr,
        )
        return 1

    print(f"\n🚀 Iniciando ingestão normativa de {len(files_to_process)} arquivo(s)...")
    print(f"📦 Provedor: {cli_args.provider or 'padrão'} | Batch size: {cli_args.batch_size}\n")

    has_errors = False
    for file in files_to_process:
        print(f"📄 Processando: {file.name} ...", end=" ", flush=True)
        res = await ingest_normative_file(
            file_path=file,
            provider=cli_args.provider,
            batch_size=cli_args.batch_size,
        )

        if res.status == "success":
            print(
                f"✅ Concluído! Norma: {res.document_code} (Rev: {res.revision}) - "
                f"{res.total_chunks} chunks indexados em {res.duration_seconds}s"
            )
        else:
            print(f"❌ Falha: {res.error_message}")
            has_errors = True

    print("\n🏁 Finalizado!")
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
