# Spec: Reranker Cross-Encoder e Reescrita Contextual de Query Multi-Turn (rag-reranker-rewriter)

## Requirements

### Requirement: Reescrita Contextual de Queries Multi-Turn (QueryRewriter)
O sistema DEVE fornecer o componente `QueryRewriter` para reformular perguntas de usuários inseridas em diálogos multi-turn, tornando-as auto-suficientes com termos normativos da Neoenergia (DIS-NOR-030 e DIS-NOR-053), preservando a intenção original sem alucinações.

#### Scenario: Bypass imediato no primeiro turno sem histórico de mensagens
- **GIVEN** uma consulta técnica do usuário e um histórico de conversa vazio (`[]`) ou `None`
- **WHEN** o método `rewrite()` de `QueryRewriter` for executado
- **THEN** ele deve retornar a consulta original limpa (`query.strip()`) imediatamente, sem invocar o modelo de linguagem (LLM).

#### Scenario: Bypass quando reescritor estiver desabilitado via configuração
- **GIVEN** a configuração `query_rewriter_enabled=False` no objeto `Settings`
- **WHEN** o método `rewrite()` for executado mesmo com histórico preenchido
- **THEN** ele deve retornar a consulta original limpa sem invocar a LLM.

#### Scenario: Reescrita contextual multi-turn com resolução de anáforas e normas
- **GIVEN** um histórico multi-turn contendo menções prévias a ramais prediais ou normas e uma nova pergunta contendo pronomes (ex.: "E se for acima de 40 apartamentos? Qual a demanda?")
- **WHEN** o método `rewrite()` for executado com `query_rewriter_enabled=True`
- **THEN** a LLM deve ser consultada com o histórico e gerar uma pergunta autônoma desambiguada e contextualizada com termos técnicos aplicáveis.

#### Scenario: Fallback gracioso em falha da chamada à LLM
- **GIVEN** uma falha de comunicação, timeout ou exceção interna ao invocar a LLM no reescritor
- **WHEN** o método `rewrite()` capturar o erro
- **THEN** ele deve registrar log do evento e retornar silenciosamente a consulta original limpa (`query.strip()`), sem propagar exceção que quebre a cadeia RAG.

### Requirement: Reordenação Semântica Listwise de Fragmentos (NormativeReranker)
O sistema DEVE fornecer o componente `NormativeReranker` para reordenar os fragmentos normativos recuperados pelo retriever vetorial por meio de julgamento semântico listwise via LLM, preservando apenas os `top_n` fragmentos mais estritamente pertinentes.

#### Scenario: Bypass quando reranker desabilitado ou número de fragmentos menor ou igual a top_n
- **GIVEN** `reranker_enabled=False` nas configurações ou uma lista de fragmentos onde `len(chunks) <= top_n`
- **WHEN** o método `rerank()` for invocado
- **THEN** ele deve retornar os fragmentos originais fatiados até `top_n` sem invocar a LLM.

#### Scenario: Reordenação listwise via LLM gerando array JSON de índices
- **GIVEN** uma lista de fragmentos candidatos (`RetrievedChunk`) e uma pergunta técnica
- **WHEN** o método `rerank()` for invocado com `reranker_enabled=True`
- **THEN** a LLM deve avaliar conjuntamente os fragmentos e produzir um array JSON com os índices dos fragmentos mais relevantes, retornando a nova lista reordenada contendo os `top_n` melhores fragmentos.

#### Scenario: Fallback gracioso para ordenação original por cosseno sob erro ou JSON inválido
- **GIVEN** uma exceção na LLM, resposta com markdown corrompido ou JSON inválido retornado na avaliação listwise
- **WHEN** o método `rerank()` tentar processar o resultado
- **THEN** ele deve registrar log da falha e retornar a lista original preservando a ordenação original por score de similaridade de cosseno truncada em `top_n`.

#### Scenario: Customização do parâmetro top_n
- **GIVEN** uma requisição explícita definindo `top_n=3` diferente do padrão
- **WHEN** o método `rerank(query, chunks, top_n=3)` for executado
- **THEN** a lista retornada deve respeitar o limite máximo de 3 fragmentos.

### Requirement: Orquestração da Cadeia RAG de Contexto (RagContextOrchestrator)
O sistema DEVE fornecer a classe `RagContextOrchestrator` responsável por coordenar a sequência completa: histórico ➔ reescrita da query ➔ busca vetorial ➔ reranking semântico ➔ `RetrievalResult`.

#### Scenario: Pipeline orquestrado completo com sucesso
- **GIVEN** um histórico multi-turn, uma nova dúvida do usuário e instâncias ativas de `NormativeRetriever`, `QueryRewriter` e `NormativeReranker`
- **WHEN** o método `get_context()` for executado
- **THEN** a query deve ser reescrita se aplicável, o retriever deve buscar os candidatos com a query reescrita, o reranker deve refinar a ordenação dos fragmentos e o resultado deve ser consolidado em um `RetrievalResult` contendo os chunks finais selecionados e a query reescrita (ou original).

#### Scenario: Curto-circuito defensivo em contingência do retriever
- **GIVEN** uma consulta que resulte em contingência no `NormativeRetriever` (`is_contingency=True`, ex.: nenhum fragmento acima do threshold)
- **WHEN** o método `get_context()` processar a resposta do retriever
- **THEN** o orquestrador DEVE retornar o `RetrievalResult` de contingência imediatamente, sem acionar o `NormativeReranker`.

#### Scenario: Operação resiliente com rewriter ou reranker ausentes ou desabilitados
- **GIVEN** instâncias de `RagContextOrchestrator` inicializadas sem `rewriter` e/ou sem `reranker` (ou com flags desligadas)
- **WHEN** o método `get_context()` for executado
- **THEN** a orquestração deve executar as etapas presentes de forma transparente sem falhas.

### Requirement: Parâmetros de Reranking e Reescrita em Configurações Centrais (Settings)
As configurações de sistema em `src/lumi/core/config.py` DEVEM incluir `reranker_enabled: bool = True`, `reranker_top_n: int = 5` e `query_rewriter_enabled: bool = True`.

#### Scenario: Valores padrão atualizados em Settings
- **WHEN** uma instância de `Settings` for carregada sem variáveis de ambiente específicas
- **THEN** `settings.reranker_enabled` deve ser `True`, `settings.reranker_top_n` deve ser `5` e `settings.query_rewriter_enabled` deve ser `True`.
