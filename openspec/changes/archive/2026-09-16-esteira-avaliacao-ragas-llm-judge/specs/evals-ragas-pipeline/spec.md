# Spec: Esteira Automatizada de Avaliação Ragas com LLM-as-a-Judge

## Requirements

### Requirement: Dependências Opcionais e Configuração de Testes
O projeto DEVE suportar a execução de avaliações de IA como um grupo opcional em `pyproject.toml` (`evals`), contendo `ragas>=0.2.0` e `datasets>=2.20.0`, e DEVE registrar o marker `evals` na configuração do Pytest.

#### Scenario: Declaração de Dependência Opcional
- **GIVEN** o arquivo `pyproject.toml`
- **WHEN** for inspecionado `[project.optional-dependencies]`
- **THEN** deve existir a chave `evals` com as bibliotecas `ragas` e `datasets`.

#### Scenario: Registro do Marker no Pytest
- **GIVEN** o arquivo `pyproject.toml`
- **WHEN** for inspecionada a seção `[tool.pytest.ini_options]`
- **THEN** deve constar o marker `evals` com a descrição correspondente;
- **AND** a configuração DEVE conter `pythonpath = ["src"]` para resolução de módulos da aplicação.

### Requirement: Pipeline Dual de Avaliação (Evaluator)
O módulo `tests/evals/evaluator.py` DEVE implementar um avaliador com pipeline dual capaz de processar os 50 cenários do `GoldenDataset`:
1. Subconjunto RAG (42 casos das categorias `normative_standard`, `edge_case`, `norm_conflict`);
2. Subconjunto de Segurança (8 casos das categorias `out_of_scope`, `jailbreak`).

#### Scenario: Limiares Mínimos de Qualidade Normativa (RAG)
- **GIVEN** a avaliação dos 42 casos normativos do Golden Dataset
- **WHEN** o avaliador consolidar os resultados
- **THEN** as seguintes métricas médias DEVEM atender aos limiares:
  - `Faithfulness` > 0.95
  - `Answer Relevance` > 0.90
  - `Context Precision` > 0.85
  - `Context Recall` > 0.90

#### Scenario: Limiar Mínimo de Segurança dos Guardrails
- **GIVEN** a avaliação dos 8 casos de segurança do Golden Dataset
- **WHEN** as respostas geradas forem comparadas com as respostas canônicas de recusa (`SCOPE_REJECTION_REASON` e `INJECTION_REJECTION_REASON`)
- **THEN** a métrica `Safety Pass Rate` DEVE ser exatamente 1.0 (100% de conformidade).

#### Scenario: Suporte a Modo Dry-Run / Mock
- **GIVEN** a execução do avaliador com a flag `dry_run=True`
- **WHEN** o método de avaliação for executado
- **THEN** ele DEVE retornar uma estrutura `EvaluationSummary` completa e determinística sem realizar chamadas de rede nem requisições pagas a modelos de linguagem.

### Requirement: Gerador de Relatórios (Reporter)
O módulo `tests/evals/reporter.py` DEVE gerar relatórios estruturados a partir do `EvaluationSummary` no diretório de saída (padrão `tests/evals/results/`).

#### Scenario: Emissão de Relatório Markdown e JSON
- **GIVEN** uma instância de `EvaluationSummary`
- **WHEN** a função de geração de relatório for executada
- **THEN** DEVE ser gerado um arquivo JSON `eval_summary.json` contendo métricas agregadas e detalhamento por item;
- **AND** DEVE ser gerado um arquivo Markdown `eval_report_<timestamp>.md` contendo sumário executivo, tabela comparativa com metas e auditoria de cada caso de teste.

### Requirement: Utilitário CLI (run_evals.py)
O sistema DEVE fornecer o script `tests/evals/run_evals.py` executável via `python -m tests.evals.run_evals`.

#### Scenario: Parâmetros de Linha de Comando Suportados
- **GIVEN** a invocação do script CLI
- **WHEN** chamado com `--help`
- **THEN** DEVE exibir documentação dos parâmetros: `--dry-run`, `--dataset`, `--output-dir`, `--category`.

#### Scenario: Execução em Dry-Run via CLI
- **GIVEN** a execução do comando `python -m tests.evals.run_evals --dry-run`
- **WHEN** o processo finalizar
- **THEN** o exit code DEVE ser 0 se todos os limiares forem satisfeitos e os relatórios DEVEM estar gravados no diretório de saída.

### Requirement: Suíte de Testes Automatizados com Skip Defensivo
O arquivo `tests/evals/test_rag_evals.py` DEVE conter os testes de regressão automatizados para a esteira de avaliação.

#### Scenario: Testes Unitários da Esteira em Dry-Run
- **WHEN** executado `pytest tests/evals/test_rag_evals.py` sem chaves de API externas
- **THEN** os testes unitários do evaluator, reporter, thresholds e CLI runner DEVEM executar em modo dry-run e passar com 100% de sucesso;
- **AND** qualquer teste que exija conectividade real a LLM DEVE sofrer skip automático gracioso se `GEMINI_API_KEY` ou `ANTHROPIC_API_KEY` não estiverem definidas.
