"""Módulo de reranking semântico listwise para fragmentos normativos recuperados."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from lumi.core.config import Settings, get_settings
from lumi.rag.llm_factory import get_llm
from lumi.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = structlog.get_logger(__name__)

RERANKER_SYSTEM_PROMPT: str = """Você é um especialista em engenharia elétrica e avaliação de relevância de normas técnicas da Neoenergia (DIS-NOR-030 e DIS-NOR-053).
Sua tarefa é avaliar uma lista de fragmentos normativos candidatos recuperados para uma pergunta técnica e reordená-los por ordem decrescente de pertinência técnica direta para responder à dúvida.

Diretrizes:
1. Analise o teor normativo, regras de instalação, tabelas e fórmulas de cada fragmento em relação à pergunta.
2. Priorize fragmentos que respondam diretamente ao parâmetro ou exigência solicitada em detrimento de fragmentos introdutórios ou contextuais genéricos.
3. Retorne EXCLUSIVAMENTE um array JSON contendo os índices inteiros dos fragmentos mais relevantes, ordenados do mais relevante para o menos relevante (exemplo: [2, 0, 4, 1, 3]).
4. NÃO inclua justificativas, markdown adicional, preâmbulo ou qualquer outro texto além do array JSON.
"""


class NormativeReranker:
    """Componente de reordenação semântica listwise via modelo de linguagem."""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Inicializa o reranker com LLM e configurações do sistema."""
        self.settings = settings or get_settings()
        self.llm = llm or get_llm(settings=self.settings)

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Reordena semanticamente os fragmentos candidatos com base na consulta do usuário.

        Aplica avaliação listwise solicitando ao modelo um array JSON de índices dos fragmentos mais
        relevantes. Caso desabilitado via configuração, ou se a quantidade de chunks for menor ou
        igual a top_n, efetua bypass preservando a ordenação original por similaridade de cosseno.
        Em qualquer situação de falha na LLM ou parsing do JSON, aplica fallback transparente para chunks[:top_n].

        Args:
            query: Pergunta técnica do usuário (original ou reescrita).
            chunks: Lista de fragmentos candidatos recuperados do banco vetorial.
            top_n: Quantidade máxima de fragmentos finais a preservar (padrão: settings.reranker_top_n).

        Returns:
            list[RetrievedChunk]: Lista dos top_n fragmentos reordenados.
        """
        effective_top_n = (
            top_n if top_n is not None else self.settings.reranker_top_n
        )

        if not chunks:
            return []

        # Bypass se desabilitado por configuração ou se quantidade de chunks for <= top_n
        if not self.settings.reranker_enabled or len(chunks) <= effective_top_n:
            logger.debug(
                "reranker_bypass",
                enabled=self.settings.reranker_enabled,
                chunk_count=len(chunks),
                top_n=effective_top_n,
            )
            return chunks[:effective_top_n]

        logger.debug(
            "reranker_started",
            query=query,
            chunk_count=len(chunks),
            top_n=effective_top_n,
        )

        # Formata fragmentos candidatos numerados de 0 a len(chunks)-1
        formatted_candidates: list[str] = []
        for idx, chunk in enumerate(chunks):
            sec = chunk.section_code or chunk.section_title or "Geral"
            pag = chunk.page_number if chunk.page_number is not None else "N/A"
            formatted_candidates.append(
                f"[{idx}] Norma: {chunk.document_code} | Seção: {sec} | Pág: {pag}\n{chunk.content}"
            )
        candidates_str = "\n\n".join(formatted_candidates)

        prompt_user = (
            f"Pergunta do usuário: {query}\n\n"
            f"Fragmentos candidatos:\n{candidates_str}\n\n"
            f"Retorne o array JSON com até {effective_top_n} índices ordenados por relevância:"
        )

        messages = [
            SystemMessage(content=RERANKER_SYSTEM_PROMPT),
            HumanMessage(content=prompt_user),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            raw_content = str(response.content).strip()

            # Extração defensiva de bloco JSON
            json_match = re.search(r"\[[\s\S]*?\]", raw_content)
            if not json_match:
                logger.warning(
                    "reranker_json_not_found_fallback",
                    raw_response=raw_content,
                )
                return chunks[:effective_top_n]

            parsed_indices = json.loads(json_match.group(0))
            if not isinstance(parsed_indices, list):
                logger.warning("reranker_invalid_json_type_fallback", raw_response=raw_content)
                return chunks[:effective_top_n]

            # Valida e filtra índices numéricos no intervalo correto sem duplicatas
            selected_indices: list[int] = []
            seen_indices: set[int] = set()

            for item in parsed_indices:
                if isinstance(item, int) and 0 <= item < len(chunks):
                    if item not in seen_indices:
                        selected_indices.append(item)
                        seen_indices.add(item)

            # Completa com índices originais restantes se a lista selecionada for menor que top_n
            if len(selected_indices) < effective_top_n:
                for idx in range(len(chunks)):
                    if idx not in seen_indices:
                        selected_indices.append(idx)
                        seen_indices.add(idx)
                    if len(selected_indices) == effective_top_n:
                        break

            final_indices = selected_indices[:effective_top_n]
            reranked_chunks = [chunks[i] for i in final_indices]

            logger.info(
                "reranker_success",
                selected_indices=final_indices,
                top_n=effective_top_n,
            )
            return reranked_chunks

        except Exception as exc:
            logger.warning(
                "reranker_fallback_on_error",
                error=str(exc),
                exc_info=True,
            )
            return chunks[:effective_top_n]
