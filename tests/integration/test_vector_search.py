"""Testes de integração para persistência e busca vetorial no pgvector (NormativeVectorStore)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.db.vector_store import NormativeVectorStore
from lumi.ingestion.models import NormativeChunkData


def make_embedding(dominant_index: int, dim: int = 768) -> list[float]:
    """Gera um vetor unitário sintético com 1.0 no índice dominante e 0.0 nas demais posições."""
    vec = [0.0] * dim
    vec[dominant_index] = 1.0
    return vec


def make_blended_embedding(
    idx1: int, idx2: int, weight1: float, weight2: float, dim: int = 768
) -> list[float]:
    """Gera um vetor normalizado sintético com pesos em duas coordenadas conhecidas."""
    import math

    vec = [0.0] * dim
    vec[idx1] = weight1
    vec[idx2] = weight2
    norm = math.sqrt(weight1**2 + weight2**2)
    return [v / norm for v in vec]


@pytest.mark.integration
class TestVectorSearchIntegration:
    """Valida o comportamento de persistência idempotente e recuperação vetorial via pgvector."""

    @pytest.mark.asyncio
    async def test_upsert_and_similarity_search(self, db_session: AsyncSession) -> None:
        """Deve persistir documento com chunks e recuperar por similaridade de cosseno."""
        store = NormativeVectorStore(session=db_session)

        # Chunks sintéticos para DIS-NOR-030
        chunk1 = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content="Instalação de postes e afastamentos mínimos de segurança na rede aérea.",
            section_code="4.2",
            section_title="Afastamentos Mínimos",
            page_number=12,
            metadata={"chapter": 4},
        )
        chunk2 = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content="Queda de tensão admissível em circuitos secundários de baixa tensão.",
            section_code="5.1",
            section_title="Dimensionamento Elétrico",
            page_number=25,
            metadata={"chapter": 5},
        )

        # Vetores ortogonais sintéticos de dimensão 768
        emb1 = make_embedding(0)  # [1, 0, 0, ...]
        emb2 = make_embedding(1)  # [0, 1, 0, ...]

        inserted_count = await store.upsert_document_with_chunks(
            document_code="DIS-NOR-030",
            title="Norma Técnica de Distribuição",
            revision="07",
            chunks_data=[chunk1, chunk2],
            embeddings=[emb1, emb2],
        )
        assert inserted_count == 2

        # Busca com vetor idêntico a emb1 -> similaridade esperada próxima a 1.0
        query_emb = make_embedding(0)
        results = await store.search_similar(
            query_embedding=query_emb,
            top_k=5,
            threshold=0.70,
        )

        assert len(results) >= 1
        top_chunk, score = results[0]
        assert top_chunk.section_code == "4.2"
        assert score >= 0.99  # Idêntico ao vetor gravado

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, db_session: AsyncSession) -> None:
        """Chunks com similaridade abaixo de 0.70 devem ser descartados da busca."""
        store = NormativeVectorStore(session=db_session)

        # Vetores com similaridades conhecidas em relação a [1.0, 0.0, ...]
        # Vetor 1: idêntico -> sim = 1.0
        emb_high = make_embedding(10)
        # Vetor 2: 45 graus -> sim ~ 0.707 (passa no threshold 0.70)
        emb_medium = make_blended_embedding(10, 11, 0.71, 0.70)
        # Vetor 3: muito distante -> sim ~ 0.10 (deve ser cortado)
        emb_low = make_blended_embedding(10, 12, 0.1, 0.99)

        chunks = [
            NormativeChunkData(
                document_code="DIS-NOR-030",
                revision="07",
                content="Conteúdo altamente similar sobre conexões.",
                section_code="1.1",
                page_number=1,
            ),
            NormativeChunkData(
                document_code="DIS-NOR-030",
                revision="07",
                content="Conteúdo medianamente similar dentro do limiar.",
                section_code="1.2",
                page_number=2,
            ),
            NormativeChunkData(
                document_code="DIS-NOR-030",
                revision="07",
                content="Conteúdo com similaridade irrelevante.",
                section_code="1.3",
                page_number=3,
            ),
        ]

        await store.upsert_document_with_chunks(
            document_code="DIS-NOR-030",
            title="Norma Técnica de Distribuição",
            revision="07",
            chunks_data=chunks,
            embeddings=[emb_high, emb_medium, emb_low],
        )

        query = make_embedding(10)
        results = await store.search_similar(
            query_embedding=query,
            top_k=10,
            threshold=0.70,
        )

        returned_sections = [chunk.section_code for chunk, _ in results]
        assert "1.1" in returned_sections
        assert "1.3" not in returned_sections  # Cortado pelo threshold

    @pytest.mark.asyncio
    async def test_document_isolation_filtering(self, db_session: AsyncSession) -> None:
        """Filtro document_code deve isolar estritamente os chunks pertencentes à norma especificada."""
        store = NormativeVectorStore(session=db_session)

        emb_target = make_embedding(20)

        chunk_doc_a = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content="Norma 030 - Regra A",
            section_code="SEC-30",
            page_number=5,
        )
        chunk_doc_b = NormativeChunkData(
            document_code="DIS-NOR-053",
            revision="03",
            content="Norma 053 - Regra B idêntica em embedding",
            section_code="SEC-53",
            page_number=8,
        )

        await store.upsert_document_with_chunks(
            document_code="DIS-NOR-030",
            title="Norma DIS 30",
            revision="07",
            chunks_data=[chunk_doc_a],
            embeddings=[emb_target],
        )
        await store.upsert_document_with_chunks(
            document_code="DIS-NOR-053",
            title="Norma DIS 53",
            revision="03",
            chunks_data=[chunk_doc_b],
            embeddings=[emb_target],
        )

        # Busca filtrada exclusivamente para DIS-NOR-053
        results = await store.search_similar(
            query_embedding=emb_target,
            top_k=5,
            threshold=0.70,
            document_code="DIS-NOR-053",
        )

        assert len(results) == 1
        chunk, _ = results[0]
        assert chunk.section_code == "SEC-53"

    @pytest.mark.asyncio
    async def test_search_similar_edge_cases(self, db_session: AsyncSession) -> None:
        """Parâmetros inválidos ou query vazia devem retornar lista vazia sem exceção."""
        store = NormativeVectorStore(session=db_session)

        # Top_k <= 0
        assert await store.search_similar(query_embedding=make_embedding(1), top_k=0) == []
        assert await store.search_similar(query_embedding=make_embedding(1), top_k=-1) == []

        # Query embedding vazia
        assert await store.search_similar(query_embedding=[], top_k=5) == []
