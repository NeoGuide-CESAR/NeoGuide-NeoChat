# Design: Ajustes Defensivos na Ingestão, Resiliência do Chat Service e Documentação Operacional Local

## Arquitetura & Fluxo de Dados

### 1. Ingestão Resiliente e Desduplicação Normativa
```mermaid
flowchart TD
    A["Diretório de Normas"] --> B["Escanear .md e .pdf"]
    B --> C["Filtrar prefixo DIS-NOR"]
    C --> D{"Mesmo radical (stem)?"}
    D -->|Sim| E["Priorizar .md e descartar .pdf duplicado"]
    D -->|Não| F["Manter arquivo único"]
    E & F --> G["Parser e Chunking Híbrido"]
    G --> H["Geração de Embeddings em Lotes (64 chunks)"]
    H --> I{"Erro 429 / ResourceExhausted?"}
    I -->|Sim| J["_extract_retry_delay: Extrair tempo recomendado"]
    J --> K["Aviso no terminal e sleep assíncrono"]
    K --> H
    I -->|Não| L["Indexação no pgvector"]
```

### 2. Resiliência Conversacional e Tolerância a Falhas no Chat
```mermaid
sequenceDiagram
    autonumber
    actor User as Cliente / Frontend
    participant CS as ChatService
    participant DB as Sessão / Banco
    participant RAG as RagContextOrchestrator
    participant LLM as BaseChatModel (Gemini)

    User->>CS: POST /api/v1/chat (request)
    CS->>DB: add_message(role='user', sanitized_text)
    CS->>DB: commit() imediato (Persistência Garantida)
    CS->>RAG: get_context(query)
    RAG-->>CS: rag_result (contexto e fontes)
    CS->>LLM: ainvoke(prompt_messages)
    alt Falha de sobrecarga / rede na LLM
        LLM-->>CS: Exception (HTTP 503 / Timeout)
        CS->>CS: Log estruturado (chat_service_llm_invoke_error)
        CS-->>User: HTTPException(503, "O modelo está temporariamente sobrecarregado...")
    else Sucesso na geração
        LLM-->>CS: AIMessage(content)
        CS-->>User: ChatResponse (200 OK)
    end
```

## Decisões Técnicas

1. **Backoff Dinâmico Adaptativo (`_extract_retry_delay`)**:
   - A API do Google pode retornar mensagens como `"Please retry after 23.4s"`. Extrair esse valor via regex permite respeitar exatamente a janela de retenção do provedor, evitando loops excessivos de retentativas prematuras.
2. **Priorização de Markdown sobre PDF na Ingestão**:
   - Quando tanto a norma formatada em Markdown quanto o PDF original coexistem na pasta de ingestão, o Markdown preserva fidelidade semântica de tabelas e cabeçalhos já higienizados, economizando tokens e evitando poluição da base vetorial com fragmentos duplicados.
3. **Commit Antecipado no ChatService**:
   - Manter a mensagem do usuário salva mesmo que o LLM falhe permite que a interface mostre o histórico real do que o usuário enviou, facilitando o reenvio subsequente sem perda de contexto conversacional.
4. **Tratamento Específico com HTTP 503**:
   - Ao traduzir falhas transitórias do LLM para HTTP 503 Service Unavailable, a API sinaliza explicitamente aos clientes HTTP (e proxies) que o serviço está momentaneamente indisponível e deve ser tentado novamente com backoff.
