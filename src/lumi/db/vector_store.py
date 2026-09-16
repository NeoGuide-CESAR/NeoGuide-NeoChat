from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lumi.db.models import NormativeChunk, NormativeDocument

if TYPE_CHECKING:
    from lumi.ingestion.models import NormativeChunkData


class NormativeVectorStore:
    """Repositório de persistência e recuperação vetorial de documentos e chunks normativos."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicializa o repositório com uma sessão assíncrona SQLAlchemy."""
        self.session = session

    async def upsert_document_with_chunks(
        self,
        document_code: str,
        title: str,
        revision: str,
        chunks_data: list[NormativeChunkData],
        embeddings: list[list[float]],
    ) -> int:
        """Persiste ou atualiza atomicamente um documento normativo e seus chunks vetorizados.

        Garante idempotência estrita: caso o documento já exista, atualiza seus metadados e
        remove todos os chunks anteriores associados antes de inserir os novos tensores.

        Args:
            document_code: Código identificador da norma (ex.: 'DIS-NOR-030').
            title: Título descritivo da norma técnica.
            revision: Versão/revisão do documento (ex.: '07' ou 'REV07').
            chunks_data: Coleção estruturada de fragmentos semânticos.
            embeddings: Lista de tensores vetoriais com dimensões compatíveis.

        Returns:
            int: Quantidade total de chunks inseridos no banco.

        Raises:
            ValueError: Se o número de chunks e o número de vetores de embeddings forem divergentes.
        """
        if len(chunks_data) != len(embeddings):
            raise ValueError(
                f"Contagens divergentes de chunks e embeddings: "
                f"{len(chunks_data)} chunks vs {len(embeddings)} vetores de embedding."
            )

        # 1. Localiza ou instancia o NormativeDocument correspondente
        stmt = select(NormativeDocument).where(NormativeDocument.code == document_code)
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc is None:
            doc = NormativeDocument(
                code=document_code,
                title=title,
                revision=revision,
            )
            self.session.add(doc)
            await self.session.flush()
        else:
            doc.title = title
            doc.revision = revision
            # Idempotência estrita: remove todos os chunks prévios da norma
            await self.session.execute(
                delete(NormativeChunk).where(NormativeChunk.document_id == doc.id)
            )
            await self.session.flush()

        # 2. Insere todos os novos chunks em lote
        chunk_entities: list[NormativeChunk] = []
        for chunk, emb in zip(chunks_data, embeddings, strict=True):
            chunk_entities.append(
                NormativeChunk(
                    document_id=doc.id,
                    content=chunk.content,
                    embedding=emb,
                    section_code=chunk.section_code,
                    section_title=chunk.section_title,
                    page_number=chunk.page_number,
                    metadata_=chunk.metadata,
                )
            )

        if chunk_entities:
            self.session.add_all(chunk_entities)
            await self.session.flush()

        return len(chunk_entities)

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.70,
        document_code: str | None = None,
    ) -> list[tuple[NormativeChunk, float]]:
        """Recupera chunks normativos mais próximos por similaridade de cosseno via pgvector (<=>).

        Calcula a similaridade através de `1.0 - distance`, filtrando por limiar mínimo e
        ordenando crescentemente pela distância de cosseno.

        Args:
            query_embedding: Vetor denso correspondente à pergunta do usuário.
            top_k: Quantidade máxima de fragmentos a retornar.
            threshold: Limiar mínimo de similaridade de cosseno (entre 0.0 e 1.0).
            document_code: Filtro opcional para restringir a busca a uma norma específica.

        Returns:
            list[tuple[NormativeChunk, float]]: Lista de tuplas (chunk, similaridade_score).
        """
        if top_k <= 0 or not query_embedding:
            return []

        distance_expr = NormativeChunk.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        stmt = select(NormativeChunk, similarity_expr).options(
            selectinload(NormativeChunk.document)
        )

        if document_code:
            stmt = stmt.join(
                NormativeDocument,
                NormativeChunk.document_id == NormativeDocument.id,
            ).where(NormativeDocument.code == document_code)

        stmt = stmt.where(similarity_expr >= threshold).order_by(distance_expr.asc()).limit(top_k)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [(row[0], float(row[1])) for row in rows]
