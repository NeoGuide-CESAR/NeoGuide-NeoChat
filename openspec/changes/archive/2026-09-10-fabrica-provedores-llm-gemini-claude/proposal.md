# Proposal: Fábrica de Provedores de LLM e Embeddings Desacoplada (Gemini e Claude)

## Context
O Lumi (NeoGuide) opera como assistente normativo inteligente para infraestrutura de telecomunicações, auxiliando projetistas e engenheiros na conformidade com normas técnicas (DIS-NOR-030 e DIS-NOR-053). Para geração de respostas contextuais e busca semântica, o sistema necessita de modelos de linguagem (LLMs) e modelos de embeddings vetoriais. Conforme definido no requisito não-funcional **RNF-06 (Portabilidade de LLMs)** e na arquitetura do sistema, o Google Gemini é estabelecido como provedor primário (ótimo custo-benefício e ampla janela de contexto), enquanto o Anthropic Claude atua como provedor alternativo/fallback configurável.

## Motivation & Value
O acoplamento direto do código a SDKs ou classes concretas de um único provedor de IA viola o Princípio da Inversão de Dependência (DIP) e encarece a manutenção ou migração de modelos. Uma fábrica desacoplada (`llm_factory.py`) padroniza a instanciação de modelos LangChain (`ChatGoogleGenerativeAI`, `ChatAnthropic`) e de embeddings (`GoogleGenerativeAIEmbeddings`, `FakeEmbeddings`), permitindo:
1. Chaveamento simples de provedores via variáveis de ambiente (`DEFAULT_LLM_PROVIDER`, `DEFAULT_EMBEDDING_PROVIDER`).
2. Execução de testes unitários e de integração rápidos, determinísticos e sem custos de rede utilizando `FakeEmbeddings`.
3. Validação estrita da dimensionalidade vetorial (768 dimensões) alinhada ao esquema do banco relacional PostgreSQL com extensão pgvector (RNF-06 / TECH-02).

## Scope
### In-Scope
- Configuração de propriedades de provedor padrão no `Settings` (`default_llm_provider`, `default_embedding_provider`).
- Implementação de `src/lumi/rag/llm_factory.py` contendo:
  - Função `get_llm(provider: str | None = None, settings: Settings | None = None, **kwargs: Any) -> BaseChatModel`.
  - Função `get_embeddings(provider: str | None = None, settings: Settings | None = None, **kwargs: Any) -> Embeddings`.
  - Função `validate_embedding_dimension(embedding: Sequence[float] | list[float], expected_dimension: int | None = None, settings: Settings | None = None) -> bool`.
- Exportação de `get_llm`, `get_embeddings` e `validate_embedding_dimension` em `src/lumi/rag/__init__.py`.
- Suporte aos provedores de LLM: `gemini` (Google Gemini) e `claude`/`anthropic` (Anthropic Claude).
- Suporte aos provedores de embeddings: `gemini` (`GoogleGenerativeAIEmbeddings`) e `fake` (`FakeEmbeddings` com 768 dimensões para testes).
- Tratamento de exceções com `ValueError` claro para provedores não suportados ou ausência de credenciais essenciais.
- Suíte completa de testes unitários com mocks em `tests/unit/test_llm_factory.py`.
- Atualização do arquivo `.env.example` com as variáveis de provedores padrão.

### Out-of-Scope
- Implementação da cadeia RAG (`chains.py`) e do retriever (`retriever.py`) — cobertos pelas tasks FEAT-05 e FEAT-06.
- Fallback automático em runtime com retries entre diferentes provedores (a troca é declarativa via configuração).
