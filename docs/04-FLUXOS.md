# 04. Fluxos do Projeto -- Lumi

## 1. Fluxo de Ingestao e Processamento Normativo (Offline / Batch)

Este fluxo e executado periodicamente pela equipe tecnica ou via comando de CLI sempre que uma nova norma for homologada ou sofrer revisao pela concessionaria.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Engenheiro / Curador
    participant CLI as CLI Ingestao (Lumi)
    participant Parser as Markdown/PDF Loader
    participant Splitter as Recursive Semantic Splitter
    participant Embedder as Modelo de Embeddings
    participant VectorDB as PostgreSQL (pgvector)

    Dev->>CLI: Executa ingestao (ex.: DIS-NOR-030-REV07.md)
    CLI->>Parser: Carrega e higieniza documento
    Parser-->>CLI: Texto estruturado com titulos e paginas
    CLI->>Splitter: Divide em chunks respeitando tabelas e secoes
    Splitter-->>CLI: Lista de Chunks + Metadados (Pagina, Secao)
    CLI->>Embedder: Gera embeddings dos chunks em lote
    Embedder-->>CLI: Tensores vetoriais
    CLI->>VectorDB: Salva em normative_chunks com indice vetorial
    VectorDB-->>CLI: Confirmacao de persistencia
    CLI-->>Dev: Ingestao concluida com sucesso
```

---

## 2. Fluxo Conversacional de Pergunta e Resposta (RAG em Tempo Real)

Este e o fluxo principal de atendimento ao projetista eletrico navegando no Wizard NeoGuide.

```mermaid
sequenceDiagram
    autonumber
    actor User as Projetista Eletrico
    participant Frontend as Wizard NeoGuide (UI)
    participant API as Lumi FastAPI Service
    participant Chain as LangChain RAG Orchestrator
    participant VectorDB as PostgreSQL (pgvector)
    participant Reranker as Reranker (Cross-Encoder)
    participant LLM as Modelo Generativo (Gemini / Claude)

    User->>Frontend: Digita: 'Como calcular fator de demanda para iluminacao?'
    Frontend->>API: POST /api/v1/chat (session_id, question, stream=true)
    API->>Chain: Dispara ciclo de atendimento RAG
    
    rect rgb(230, 245, 255)
        Note over Chain,LLM: Reescrita de Query Multi-Turn
        Chain->>LLM: Historico recente + Pergunta atual
        LLM-->>Chain: Query reformulada e otimizada para busca
    end

    rect rgb(240, 248, 255)
        Note over Chain,Reranker: Recuperacao Semantica + Reranking
        Chain->>VectorDB: Busca vetorial por similaridade de cosseno (Top 10~15)
        VectorDB-->>Chain: Retorna chunks candidatos + Metadados
        Chain->>Reranker: Reordena chunks por relevancia cruzada
        Reranker-->>Chain: Top 5 chunks finais (DIS-NOR-030, Pag. 42)
    end

    rect rgb(255, 250, 240)
        Note over Chain,LLM: Sintese Aumentada com Salvaguardas
        Chain->>LLM: Prompt do Sistema (Persona Lumi) + Historico + Contexto Normativo + Pergunta
        LLM-->>Chain: Streaming de Tokens (Resposta didatica + Citacao enxuta)
    end

    Chain-->>API: Yield Token Stream + Payload Final de Metadados de Fontes
    API-->>Frontend: SSE Stream (data: { token: '...' })
    API-->>Frontend: SSE Evento Final (event: sources, data: [ { norma, pagina, trecho } ])
    Frontend-->>User: Exibe resposta fluida no chat + card com link da norma
```

---

## 3. Fluxo de Tratamento para Perguntas Fora de Escopo / Sem Evidencia

Salvaguarda essencial para evitar que a Lumi alucine regras que possam causar a reprovacao do projeto na Neoenergia.

```mermaid
flowchart TD
    A[Pergunta do Projetista Recebida] --> B[Busca Vetorial no pgvector Top-K]
    B --> C{Score de Similaridade >= Threshold Minimo?}
    
    C -- Sim --> D[Injeta Chunks no Prompt de Contexto]
    D --> E[LLM Gera Resposta Instrutiva com Citacoes]
    E --> F[Retorna Resposta com Fontes Estruturadas]
    
    C -- Nao --> G[Ativa Prompt de Salvaguarda]
    G --> H[Lumi responde amigavelmente que a duvida nao consta nas normas vigentes indexadas]
    H --> I[Orienta o projetista a consultar o suporte tecnico oficial da Neoenergia]
    I --> J[Retorna resposta sem fontes vinculadas]
```

---

## 4. Diagrama de Estados da Sessao Conversacional

```mermaid
stateDiagram-v2
    [*] --> Inativa : Frontend inicializa ou carrega pagina
    Inativa --> Ativa : Primeira mensagem do usuario enviada
    Ativa --> Processando : Requisicao enviada ao backend
    state Processando {
        [*] --> BuscandoNormas
        BuscandoNormas --> SintetizandoResposta
        SintetizandoResposta --> TransmitindoTokens
        TransmitindoTokens --> [*]
    }
    Processando --> Ativa : Resposta e fontes finalizadas com sucesso
    Processando --> ErroTratado : Falha de timeout ou LLM (emite event: error via SSE)
    ErroTratado --> Ativa : Usuario reenvia pergunta ou segue nova duvida
    Ativa --> Fechada : Sessao expira ou usuario reinicia o chat
    Fechada --> [*]
```

> **Protocolo de Erro em Streaming SSE:** Caso a LLM desconecte ou falhe durante a transmissao de tokens, a API emite imediatamente um evento `event: error` com mensagem amigavel padronizada e encerra o stream. Nao ha retry no meio de uma resposta parcial para manter a coerencia do texto ja exibido ao projetista.

