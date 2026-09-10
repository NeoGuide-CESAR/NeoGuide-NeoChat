# Delta Spec: Setup do Ambiente Python

## ADDED Requirements

### Requirement: Declaração de Dependências e Build System
O projeto DEVE possuir um arquivo `pyproject.toml` na raiz configurando o pacote `lumi` com suporte a Python >= 3.12, definindo build system baseado em `hatchling` e declarando as dependências de produção e grupos de desenvolvimento.

#### Scenario: Sincronização e Lock de Dependências com uv
- **GIVEN** o repositório clonado com `uv` instalado
- **WHEN** o comando `uv lock` for executado na raiz do projeto
- **THEN** o arquivo `uv.lock` deve ser gerado determinando versões estáveis sem erros de resolução.

### Requirement: Inicialização da Aplicação FastAPI
O pacote `lumi` DEVE fornecer um ponto de entrada `src/lumi/main.py` com uma instância FastAPI configurada com metadados do projeto Lumi (NeoGuide) e endpoint raiz/diagnóstico.

#### Scenario: Resposta HTTP na Rota Raiz
- **GIVEN** a aplicação FastAPI instanciada em `src/lumi/main.py`
- **WHEN** uma requisição HTTP GET for enviada para `/` ou `/health`
- **THEN** a resposta deve retornar status 200 OK com payload JSON informativo sobre o serviço.

### Requirement: Configuração de Variáveis de Ambiente
O projeto DEVE fornecer um arquivo `.env.example` na raiz contendo todas as variáveis essenciais para o funcionamento do sistema, com comentários e valores padrão adequados para desenvolvimento local.

#### Scenario: Carregamento de Configurações Padrão
- **GIVEN** as variáveis definidas no `.env.example`
- **WHEN** inspecionadas pelo desenvolvedor ou classes Pydantic Settings
- **THEN** todas as chaves obrigatórias (DATABASE_URL, GEMINI_API_KEY, ANTHROPIC_API_KEY, API_PORT) devem estar documentadas.
