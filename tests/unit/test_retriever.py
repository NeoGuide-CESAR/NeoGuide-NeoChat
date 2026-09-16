"""Testes unitários para o módulo de recuperação vetorial, threshold e contingência (FEAT-07)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.embeddings.fake import FakeEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import Settings
from lumi.db.models import NormativeChunk, NormativeDocument
from lumi.db.vector_store import NormativeVectorStore
from lumi.rag import (
    CONTINGENCY_NO_SOURCES_MESSAGE,
    NormativeRetriever,
    RetrievalResult,
    RetrievedChunk,
)
from lumi.schemas.chat import SourceMetadata


class TestRetrievedChunk:
    """Testes unitários para a dataclass RetrievedChunk e conversão de metadados."""

    def test_retrieved_chunk_instantiation(self) -> None:
        """Valida que todos os campos são armazenados fielmente."""
        chunk_id = uuid4()
        chunk = RetrievedChunk(
            chunk_id=chunk_id,
            document_code="DIS-NOR-030",
            document_title="Critérios de Projeto de Redes de Distribuição",
            revision="REV07",
            section_code="Item 5.2",
            section_title="Dimensionamento de Ramais",
            page_number=14,
            content="O ramal de ligação deve suportar a corrente máxima calculada.",
            similarity_score=0.89,
            metadata={"chapter": 5},
        )

        assert chunk.chunk_id == chunk_id
        assert chunk.document_code == "DIS-NOR-030"
        assert chunk.document_title == "Critérios de Projeto de Redes de Distribuição"
        assert chunk.revision == "REV07"
        assert chunk.section_code == "Item 5.2"
        assert chunk.section_title == "Dimensionamento de Ramais"
        assert chunk.page_number == 14
        assert chunk.content == "O ramal de ligação deve suportar a corrente máxima calculada."
        assert chunk.similarity_score == pytest.approx(0.89)
        assert chunk.metadata == {"chapter": 5}

    def test_to_source_metadata_complete(self) -> None:
        """Garante conversão correta para o schema SourceMetadata da API."""
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-030",
            document_title="Critérios de Projeto",
            revision="REV07",
            section_code="Item 5.2",
            section_title="Dimensionamento de Ramais",
            page_number=14,
            content="Conteúdo explicativo da norma.",
            similarity_score=0.8523,
            metadata={},
        )

        source = chunk.to_source_metadata()
        assert isinstance(source, SourceMetadata)
        assert source.document_code == "DIS-NOR-030"
        assert source.revision == "REV07"
        assert source.section == "Item 5.2"
        assert source.page == 14
        assert source.relevance_score == pytest.approx(0.8523)
        assert source.snippet == "Conteúdo explicativo da norma."

    def test_to_source_metadata_fallbacks(self) -> None:
        """Valida valores de fallback seguros quando section_code ou page_number são ausentes."""
        chunk = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-053",
            document_title="Norma Predial",
            revision="",
            section_code=None,
            section_title="Disposições Gerais",
            page_number=None,
            content="Instalações prediais coletivas.",
            similarity_score=0.75,
            metadata={},
        )

        source = chunk.to_source_metadata()
        assert source.section == "Disposições Gerais"
        assert source.page == 1
        assert source.revision == ""

        # Teste quando section_code e section_title são None
        chunk_no_section = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-053",
            document_title="Norma Predial",
            revision="",
            section_code=None,
            section_title=None,
            page_number=0,  # Page deve ser ge=1
            content="Texto sem seção.",
            similarity_score=1.2,  # Score acima de 1.0 deve ser truncado para 1.0
            metadata={},
        )
        source_fallback = chunk_no_section.to_source_metadata()
        assert source_fallback.section == "Geral"
        assert source_fallback.page == 1
        assert source_fallback.relevance_score == 1.0


class TestRetrievalResult:
    """Testes unitários para a dataclass RetrievalResult e propriedades calculadas."""

    def test_retrieval_result_sources_property(self) -> None:
        """Valida que a propriedade sources gera a lista correta de SourceMetadata."""
        chunk1 = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-030",
            document_title="Critérios",
            revision="REV07",
            section_code="Item 4.1",
            section_title="Entrada de Serviço",
            page_number=10,
            content="Texto 1",
            similarity_score=0.92,
            metadata={},
        )
        chunk2 = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-053",
            document_title="Fornecimento",
            revision="REV03",
            section_code="Item 7.3",
            section_title="Quadro Geral",
            page_number=25,
            content="Texto 2",
            similarity_score=0.81,
            metadata={},
        )

        result = RetrievalResult(
            query="Como calcular a demanda?",
            chunks=[chunk1, chunk2],
            is_contingency=False,
            contingency_message=None,
        )

        sources = result.sources
        assert len(sources) == 2
        assert sources[0].document_code == "DIS-NOR-030"
        assert sources[1].document_code == "DIS-NOR-053"

    def test_retrieval_result_formatted_context(self) -> None:
        """Valida a formatação de chunks para injeção no prompt mestre RAG."""
        chunk1 = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-030",
            document_title="Critérios",
            revision="REV07",
            section_code="Item 4.1",
            section_title="Entrada de Serviço",
            page_number=10,
            content="Regra para ramal aéreo.",
            similarity_score=0.90,
            metadata={},
        )
        chunk2 = RetrievedChunk(
            chunk_id=uuid4(),
            document_code="DIS-NOR-053",
            document_title="Norma",
            revision="REV01",
            section_code=None,
            section_title="Geral",
            page_number=None,
            content="Regra geral subterrânea.",
            similarity_score=0.80,
            metadata={},
        )

        result = RetrievalResult(
            query="Tipos de ramal",
            chunks=[chunk1, chunk2],
            is_contingency=False,
        )

        expected_block_1 = "[Fonte: DIS-NOR-030, Item Item 4.1, Pág. 10]\nRegra para ramal aéreo."
        expected_block_2 = "[Fonte: DIS-NOR-053, Item Geral, Pág. N/A]\nRegra geral subterrânea."
        assert expected_block_1 in result.formatted_context
        assert expected_block_2 in result.formatted_context
        assert "\n\n" in result.formatted_context

    def test_retrieval_result_contingency_properties(self) -> None:
        """Garante que em caso de contingência as fontes e o contexto sejam vazios."""
        result = RetrievalResult(
            query="Pergunta fora de escopo",
            chunks=[],
            is_contingency=True,
            contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE,
        )

        assert result.sources == []
        assert result.formatted_context == ""
        assert result.contingency_message == CONTINGENCY_NO_SOURCES_MESSAGE


class TestNormativeRetriever:
    """Testes unitários para a classe orquestradora NormativeRetriever."""

    @pytest.fixture
    def mock_vector_store(self) -> AsyncMock:
        return AsyncMock(spec=NormativeVectorStore)

    @pytest.fixture
    def mock_embeddings(self) -> AsyncMock:
        embeddings = AsyncMock()
        embeddings.aembed_query.return_value = [0.1] * 768
        return embeddings

    @pytest.fixture
    def test_settings(self) -> Settings:
        return Settings(
            similarity_threshold=0.70,
            top_k_retrieval=10,
        )

    @pytest.mark.asyncio
    async def test_retrieve_success_above_threshold(
        self,
        mock_vector_store: AsyncMock,
        mock_embeddings: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Verifica recuperação bem-sucedida com scores >= threshold."""
        doc = NormativeDocument(
            code="DIS-NOR-030",
            title="Critérios de Projeto",
            revision="REV07",
        )
        chunk1 = NormativeChunk(
            id=uuid4(),
            document_id=doc.id,
            content="Conteúdo relevante 1",
            section_code="5.1",
            section_title="Seção 1",
            page_number=12,
            metadata_={"tag": "redes"},
        )
        chunk1.document = doc

        chunk2 = NormativeChunk(
            id=uuid4(),
            document_id=doc.id,
            content="Conteúdo relevante 2",
            section_code="5.2",
            section_title="Seção 2",
            page_number=15,
            metadata_={},
        )
        chunk2.document = doc

        mock_vector_store.search_similar.return_value = [
            (chunk1, 0.88),
            (chunk2, 0.75),
        ]

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=mock_embeddings,
            settings=test_settings,
        )

        result = await retriever.retrieve("Qual a seção mínima do condutor?")

        assert isinstance(result, RetrievalResult)
        assert result.is_contingency is False
        assert result.contingency_message is None
        assert len(result.chunks) == 2
        assert result.chunks[0].document_code == "DIS-NOR-030"
        assert result.chunks[0].similarity_score == pytest.approx(0.88)
        assert result.chunks[1].similarity_score == pytest.approx(0.75)
        assert len(result.sources) == 2
        assert "[Fonte: DIS-NOR-030, Item 5.1, Pág. 12]" in result.formatted_context

        mock_embeddings.aembed_query.assert_awaited_once_with("Qual a seção mínima do condutor?")
        mock_vector_store.search_similar.assert_awaited_once_with(
            query_embedding=[0.1] * 768,
            top_k=10,
            threshold=0.70,
            document_code=None,
        )

    @pytest.mark.asyncio
    async def test_retrieve_contingency_when_empty_results(
        self,
        mock_vector_store: AsyncMock,
        mock_embeddings: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Garante contingência quando a busca no vector store retorna lista vazia."""
        mock_vector_store.search_similar.return_value = []

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=mock_embeddings,
            settings=test_settings,
        )

        result = await retriever.retrieve("Pergunta sobre receita de bolo")

        assert result.is_contingency is True
        assert result.contingency_message == CONTINGENCY_NO_SOURCES_MESSAGE
        assert result.chunks == []
        assert result.sources == []
        assert result.formatted_context == ""

    @pytest.mark.asyncio
    async def test_retrieve_contingency_when_results_below_threshold(
        self,
        mock_vector_store: AsyncMock,
        mock_embeddings: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Garante contingência quando todos os chunks retornados ficam abaixo do threshold."""
        doc = NormativeDocument(code="DIS-NOR-030", title="Norma", revision="01")
        chunk_low = NormativeChunk(
            id=uuid4(),
            document_id=doc.id,
            content="Texto não relacionado",
            section_code="1.0",
            section_title="Intro",
            page_number=1,
            metadata_={},
        )
        chunk_low.document = doc

        # Score 0.65 abaixo do threshold configurado (0.70)
        mock_vector_store.search_similar.return_value = [(chunk_low, 0.65)]

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=mock_embeddings,
            settings=test_settings,
        )

        result = await retriever.retrieve("Tópico distante")

        assert result.is_contingency is True
        assert result.contingency_message == CONTINGENCY_NO_SOURCES_MESSAGE
        assert result.chunks == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "blank_query",
        [
            "",
            "   ",
            "\t\n  \t",
        ],
    )
    async def test_retrieve_empty_or_whitespace_query_immediate_contingency(
        self,
        mock_vector_store: AsyncMock,
        mock_embeddings: AsyncMock,
        test_settings: Settings,
        blank_query: str,
    ) -> None:
        """Garante salvaguarda defensiva retornando contingência imediatamente sem chamar IA ou DB."""
        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=mock_embeddings,
            settings=test_settings,
        )

        result = await retriever.retrieve(blank_query)

        assert result.is_contingency is True
        assert result.contingency_message == CONTINGENCY_NO_SOURCES_MESSAGE
        assert result.chunks == []
        mock_embeddings.aembed_query.assert_not_awaited()
        mock_vector_store.search_similar.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retrieve_overrides_top_k_and_threshold_and_document_code(
        self,
        mock_vector_store: AsyncMock,
        mock_embeddings: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Verifica se parâmetros de override passados a retrieve têm precedência sobre os defaults."""
        doc = NormativeDocument(code="DIS-NOR-053", title="Norma", revision="01")
        chunk = NormativeChunk(
            id=uuid4(),
            document_id=doc.id,
            content="Regra específica",
            section_code="2.1",
            section_title="Subestação",
            page_number=5,
            metadata_={},
        )
        chunk.document = doc

        mock_vector_store.search_similar.return_value = [(chunk, 0.95)]

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=mock_embeddings,
            settings=test_settings,
        )

        result = await retriever.retrieve(
            query="Subestação compartilhada",
            top_k=3,
            threshold=0.85,
            document_code="DIS-NOR-053",
        )

        assert result.is_contingency is False
        assert len(result.chunks) == 1
        mock_vector_store.search_similar.assert_awaited_once_with(
            query_embedding=[0.1] * 768,
            top_k=3,
            threshold=0.85,
            document_code="DIS-NOR-053",
        )

    @pytest.mark.asyncio
    async def test_retrieve_with_async_fake_embeddings(
        self,
        mock_vector_store: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Verifica compatibilidade direta com FakeEmbeddings assíncrono."""
        from lumi.rag.llm_factory import get_embeddings

        fake_emb = get_embeddings(provider="fake", settings=test_settings)
        mock_vector_store.search_similar.return_value = []

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=fake_emb,
            settings=test_settings,
        )

        result = await retriever.retrieve("Consulta de teste")
        assert result.is_contingency is True
        mock_vector_store.search_similar.assert_awaited_once()
        call_args = mock_vector_store.search_similar.call_args[1]
        assert len(call_args["query_embedding"]) == 768

    def test_retriever_init_with_session_creates_vector_store(self) -> None:
        """Verifica instanciação automática do NormativeVectorStore a partir da sessão SQLAlchemy."""
        mock_session = AsyncMock(spec=AsyncSession)
        fake_emb = FakeEmbeddings(size=768)

        retriever = NormativeRetriever(
            session=mock_session,
            embeddings=fake_emb,
        )

        assert retriever.vector_store is not None
        assert isinstance(retriever.vector_store, NormativeVectorStore)
        assert retriever.vector_store.session is mock_session

    @pytest.mark.asyncio
    async def test_retriever_missing_session_and_store_raises_error(self) -> None:
        """Garante lançamento de erro claro caso nem session nem vector_store sejam fornecidos ao retrieve."""
        fake_emb = FakeEmbeddings(size=768)
        retriever = NormativeRetriever(embeddings=fake_emb)

        with pytest.raises(
            RuntimeError, match="NormativeVectorStore ou AsyncSession é obrigatório"
        ):
            await retriever.retrieve("Pergunta")

    @pytest.mark.asyncio
    async def test_retrieve_with_pure_sync_embeddings(
        self,
        mock_vector_store: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Verifica compatibilidade com gerador de embeddings puramente síncrono (apenas embed_query)."""

        class SyncOnlyEmbeddings:
            def embed_query(self, text: str) -> list[float]:
                return [0.42] * 768

        sync_emb = SyncOnlyEmbeddings()
        mock_vector_store.search_similar.return_value = []

        retriever = NormativeRetriever(
            vector_store=mock_vector_store,
            embeddings=sync_emb,  # type: ignore[arg-type]
            settings=test_settings,
        )

        result = await retriever.retrieve("Pergunta síncrona")
        assert result.is_contingency is True
        mock_vector_store.search_similar.assert_awaited_once()
        call_args = mock_vector_store.search_similar.call_args[1]
        assert call_args["query_embedding"] == [0.42] * 768

    @pytest.mark.asyncio
    async def test_retrieve_with_session_initialization(
        self,
        test_settings: Settings,
    ) -> None:
        """Verifica execução de retrieve quando inicializado apenas com AsyncSession."""
        from lumi.rag.llm_factory import get_embeddings

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        fake_emb = get_embeddings(provider="fake", settings=test_settings)

        retriever = NormativeRetriever(
            session=mock_session,
            embeddings=fake_emb,
            settings=test_settings,
        )

        result = await retriever.retrieve("Pergunta com sessão")
        assert result.is_contingency is True
        mock_session.execute.assert_awaited_once()
