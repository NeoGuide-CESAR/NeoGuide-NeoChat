# Proposal: Esteira Automatizada de Avaliação Ragas com LLM-as-a-Judge

## Contexto
O assistente técnico especializado **Lumi NeoGuide** foi concebido para atuar nas normas técnicas críticas da **Neoenergia Pernambuco** (normas **DIS-NOR-030** e **DIS-NOR-053**). Em um ambiente de engenharia elétrica de alta responsabilidade, qualquer alucinação ou resposta em desacordo com as diretrizes normativas pode ocasionar desde reprovações formais de projetos até riscos severos de sobrecarga e incêndio.

Após a consolidação do catálogo curado com 50 cenários em `tests/evals/golden_dataset.json` (TECH-06), faz-se necessária a implementação da **esteira automatizada de avaliação (Evals)** utilizando o framework metodológico **Ragas** e o padrão **LLM-as-a-Judge**, dotada de pipeline dual, relatórios auditáveis e CLI integrado.

## Justificativa
1. **Pipeline Dual de Avaliação:**
   - **Subconjunto RAG (42 casos normativos):** Avalia as 4 métricas canônicas do Ragas:
     - *Faithfulness* (> 0.95): Fidelidade estrita aos fragmentos normativos recuperados.
     - *Answer Relevance* (> 0.90): Pertinência e foco da resposta gerada em relação à consulta.
     - *Context Precision* (> 0.85): Qualidade da ordenação dos trechos recuperados do pgvector.
     - *Context Recall* (> 0.90): Cobertura normativa completa necessária para o atendimento técnico.
   - **Subconjunto de Segurança (8 casos de guardrail):** Avalia os cenários de `out_of_scope` e `jailbreak`:
     - *Safety Pass Rate* (= 1.0): Conformidade absoluta com as respostas canônicas de recusa de guardrails (`SCOPE_REJECTION_REASON` e `INJECTION_REJECTION_REASON`).
2. **Execução Determinística e Dry-run:**
   - Para evitar consumo desnecessário de cotas de tokens LLM durante pipelines de CI/CD ou testes de unidade locais, a esteira deve fornecer modo `--dry-run` / mock determinístico que exercita 100% da lógica de cálculo de métricas, consolidação e relatórios sem conexões externas.
3. **Relatórios Auditáveis e Integração CLI:**
   - Geração automática de relatórios em Markdown (`eval_report_<timestamp>.md`) e JSON (`eval_summary.json`) em `tests/evals/results/`.
   - Script CLI executável via `python -m tests.evals.run_evals` com parâmetros flexíveis (`--dry-run`, `--dataset`, `--output-dir`, `--category`).
   - Suíte de testes Pytest (`tests/evals/test_rag_evals.py`) decorada com `@pytest.mark.evals` e skip defensivo automático na ausência de chaves de API.

## Escopo

### In-Scope
- Configuração de dependências opcionais em `pyproject.toml`:
  - Grupo `evals` (`ragas>=0.2.0`, `datasets>=2.20.0`).
  - Marker `evals` registrado no Pytest.
  - Inclusão de `pythonpath = ["src"]` para suporte transparente a worktrees.
- Implementação de `tests/evals/evaluator.py`:
  - Modelos de dados de resultados e limiares (`EvaluationThresholds`, `CaseEvaluationResult`, `EvaluationSummary`).
  - Lógica do pipeline dual (RAG 42 casos + Segurança 8 casos).
  - Modo dry-run / mock e integração com Ragas/LLM quando disponível.
- Implementação de `tests/evals/reporter.py`:
  - Geração de relatório analítico em Markdown (`eval_report_<timestamp>.md`).
  - Geração de sumário estruturado em JSON (`eval_summary.json`).
- Implementação do runner CLI `tests/evals/run_evals.py`:
  - Argumentos CLI `--dry-run`, `--dataset`, `--output-dir`, `--category`, `--help`.
  - Saída formatada no terminal e exit codes apropriados.
- Implementação da suíte de testes `tests/evals/test_rag_evals.py`:
  - Testes marcados com `@pytest.mark.evals`.
  - Skip defensivo automático caso chaves de API não estejam configuradas.
  - Testes em dry-run cobrindo evaluator, reporter, thresholds e CLI runner.
- Atualização da documentação técnica `docs/07-SEGURANCA-E-AVALIACAO-IA.md` (Seção 4.2).
- Sincronização canônica e arquivamento via OpenSpec SDD.

### Out-of-Scope
- Cobrança de chamadas LLM reais obrigatórias durante `pytest tests/evals/` sem flags específicas ou chaves de API.
- Alteração no fluxo de inferência em tempo de execução da API FastAPI.
