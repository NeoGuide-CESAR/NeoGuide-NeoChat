# 02. Requisitos do Projeto — Lumi

## 1. Requisitos Funcionais (RF)

### Modulo Conversacional & RAG
- **RF-01: Consulta Conversacional Especializada:** O sistema deve receber perguntas textuais em linguagem natural sobre normas tecnicas da Neoenergia e retornar respostas contextualizadas.
- **RF-02: Recuperacao Baseada em Evidencias (RAG):** O sistema deve buscar os fragmentos mais relevantes das normas (DIS-NOR-030 e DIS-NOR-053) no banco vetorial antes de gerar a resposta.
- **RF-03: Citacao Amigavel de Fontes no Texto:** O corpo da resposta gerada deve manter tom acessivel e didatico, com citacoes enxutas ao final (ex.: [Fonte: DIS-NOR-030, Item 5.2]).
- **RF-04: Metadados Estruturados de Fontes:** A API deve retornar um array de metadados em paralelo ao texto com: identificador da norma, secao, pagina original do documento, trecho do fragmento recuperado e pontuacao de similaridade/relevancia.
- **RF-05: Gerenciamento de Historico / Sessoes de Chat:** O sistema deve suportar conversas multi-turn mantendo contexto recente atraves de um session_id informado pelo cliente.
- **RF-06: Salvaguarda Anti-Alucinacao:** Quando a pergunta estiver fora do escopo normativo das fontes indexadas ou nao houver dados suficientes, o assistente deve admitir explicitamente a ausencia da informacao em vez de inventar regras.

### Pipeline de Ingestao de Documentos
- **RF-07: Ingestao e Processamento de Normas:** O sistema deve possuir rotinas CLI/scripts para extracao, limpeza e chunking hibrido de arquivos Markdown/PDF de normas tecnicas, priorizando secoes e itens normativos como unidades semanticas naturais (ex.: "5.2.1", "Tabela 3") e subdividindo secoes extensas com split por tamanho e overlap para preservar contexto.
- **RF-08: Armazenamento Vetorial e Indexacao:** O sistema deve converter fragmentos normativos em vetores densos (embeddings) e persistir no banco relacional PostgreSQL com extensao pgvector.
- **RF-09: Enriquecimento de Metadados na Ingestao:** Cada chunk vetorial deve conter metadados como: codigo da norma, revisao, capitulo, subtitulo e numero da pagina correspondente.

---

## 2. Requisitos Nao-Funcionais (RNF)

- **RNF-01: Performance & Latencia:** O tempo total de resposta (incluindo recuperacao de contexto e geracao) deve ser inferior a 3,0 segundos sob conexao padrao, tanto no modo sincrono quanto no inicio do streaming SSE.
- **RNF-02: Suporte a Streaming (SSE):** A API deve suportar Server-Sent Events (SSE) para transmissao token a token das respostas geradas, aprimorando a percepcao de tempo de resposta no frontend.
- **RNF-03: Modularidade e Desacoplamento:** O backend deve ser estritamente headless, expondo endpoints HTTP RESTful e SSE agnosticos ao consumidor (compativel com o frontend do Wizard NeoGuide ou ferramentas terceiras).
- **RNF-04: Containerizacao e Zero-Setup Local:** Toda a solucao (API FastAPI/Lumi e PostgreSQL com extensao pgvector) deve ser fornecida via `docker-compose.yml`, permitindo que qualquer desenvolvedor execute o sistema completo com `docker compose up`, sem necessidade de instalar dependencias ou bancos no host local.
- **RNF-05: Stack e Infraestrutura de Baixo Custo:** Uso de Python com uv no container, LangChain para orquestracao de RAG e banco unificado PostgreSQL + pgvector.
- **RNF-06: Portabilidade de LLMs:** A camada de LLM deve permitir chaveamento flexivel via configuracao de ambiente entre Google Gemini (ex.: gemini-1.5-pro/flash ou gemini-2.0-flash) e Anthropic Claude (ex.: claude-3-5-sonnet), alem de provedor de embeddings configuravel.
- **RNF-07: Robustez de Erros:** Respostas com erros da API do provedor de LLM ou banco vetorial devem ser tratadas graciosamente, com mensagens padronizadas em JSON sem vazamento de stack trace.
- **RNF-08: Qualidade de Codigo e Seguranca no Git (Pre-commit):** O repositorio deve possuir esteira de git hooks validando estritamente ausencia de segredos/chaves de API, formatacao (Ruff) e checagem de tipos (Mypy) antes de qualquer commit.
- **RNF-09: Rastreabilidade e Desenvolvimento Orientado por Especificacoes (SDD):** O ciclo de engenharia deve adotar o OpenSpec para propor, desenhar e aprovar tarefas antes de codificar, aliado ao Graphify para analise de impacto arquitetural e gestao de dependencias.
- **RNF-10: Autenticacao via API Key:** Todos os endpoints devem exigir autenticacao por chave de API simples via header `X-API-Key`, configuravel por variavel de ambiente. Suficiente para o escopo do MVP academico.
- **RNF-11: Rate-Limiting por Chave de API:** A API deve impor limite de 30 requisicoes por minuto por API key, protegendo contra consumo excessivo de creditos de LLM por loops acidentais ou testes automatizados.

---

## 3. Regras de Negocio (RN)

- **RN-01: Prevalencia Normativa Oficial:** A Lumi nao pode sugerir criterios de calculo divergentes do que esta expressamente previsto nas normas vigentes (DIS-NOR-030 e DIS-NOR-053).
- **RN-02: Persona Lumi:** O tom de comunicacao deve ser amigavel, empatico, objetivo e instrutivo. Jargoes normativos devem ser explicados caso solicitado.
- **RN-03: Separacao de Responsabilidade de Calculo:** Se o usuario solicitar "calcule a demanda total do meu predio de 40 apartamentos", a Lumi deve explicar o metodo, citar as tabelas e fatores aplicaveis, e orientar o usuario a utilizar os campos correspondentes do Wizard do NeoGuide.
- **RN-04: Transparencia das Fontes:** Toda afirmativa tecnica relevante deve ter seu metadado de origem associado no retorno da API.
- **RN-05: Politica de Retencao de Sessoes:** Sessoes de chat inativas por mais de 1 (uma) hora devem ser automaticamente encerradas (transicao para estado `Fechada`). O historico de mensagens permanece persistido no banco para fins de analytics e auditoria. Novas perguntas apos o TTL iniciam uma sessao nova.
