# Proposal: Suíte de Testes Unitários e de Integração de API (TECH-08)

## Context
O Lumi NeoGuide é o assistente normativo inteligente para infraestrutura de telecomunicações da Neoenergia Pernambuco.
Após a implementação das funcionalidades centrais do sistema (ingestão de normas, chunking hierárquico, busca vetorial e híbrida, reranking, guardrails de entrada e saída, streaming SSE e persistência desacoplada assíncrona), é imperativo consolidar uma suíte completa de testes automatizados com cobertura rigorosa mínima de 95% em todo o código de aplicação (`src/lumi`).

## Motivation & Value
1. **Confiabilidade e Prevenção de Regressões (RNF-04)**: Garantir que alterações no pipeline de RAG, contratos de API e modelos de persistência não quebrem fluxos existentes.
2. **Meta de Cobertura Rigorosa (>= 95%)**: Estabelecer monitoramento contínuo de cobertura de código via `pytest-cov`, identificando e cobrindo branches condicionais e tratamentos de exceção.
3. **Isolamento de Testes de Integração e Rollback Automático**: Fornecer fixtures de banco de dados com transações assíncronas isoladas e rollback automático por teste, prevenindo poluição da base de dados e garantindo skip gracioso quando PostgreSQL/pgvector não estiver acessível.
4. **Validação Fim a Fim do Fluxo Normativo (E2E)**: Simular o ciclo de vida completo de uma interação: saúde do sistema (`/health`), criação de sessão (`/api/v1/sessions`), perguntas em streaming com Server-Sent Events (`/api/v1/chat`), preservação de contexto em multi-turn, persistência assíncrona em `normative_query_analytics` e expiração de TTL.
5. **Verificação Vetorial no pgvector**: Validar o comportamento de cálculo de similaridade de cosseno, limiar de contingência (threshold 0.70) e isolamento por código de documento.

## Scope

### In-Scope
- `pyproject.toml`:
  - Adição de `pytest-cov>=5.0.0` nas dependências de desenvolvimento (`[project.optional-dependencies] dev`).
  - Registro formal dos markers `integration` e `evals`.
  - Configuração de `addopts = "-v --strict-markers"` com suporte a flags de cobertura.
- `tests/conftest.py`:
  - Fixtures assíncronas de banco de dados (`db_session`) com rollback automático e skip gracioso (`pytest.skip("PostgreSQL/pgvector não disponível no ambiente")`) quando o banco local/container não responder.
- `tests/integration/test_vector_search.py`:
  - Testes marcados com `@pytest.mark.integration` cobrindo inserção e busca vetorial por similaridade de cosseno, limiar de 0.70 e isolamento de documentos.
- `tests/integration/test_e2e_flow.py`:
  - Teste ponta a ponta cobrindo `/health`, criação de sessão, stream SSE, turnos adicionais preservando histórico, telemetria em `normative_query_analytics` e verificação de TTL.
- `tests/unit/`:
  - Cobertura adicional de branches faltantes nos módulos com gaps para assegurar meta >= 95% global e por módulo.
- `docs/06-ESTRUTURA-DE-PASTAS.md`:
  - Atualização da documentação da árvore de diretórios refletindo a suíte de testes de integração e E2E.

### Out-of-Scope
- Testes de carga distribuída (k6/locust em clusters externos).
- Testes de UI/Frontend (escopo do repositório frontend NeoGuide).
