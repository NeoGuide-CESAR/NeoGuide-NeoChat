# Spec: Golden Dataset de Avaliação de RAG (Evals)

## Requirements

### Requirement: Modelos de Dados Pydantic para o Golden Dataset
O sistema DEVE fornecer schemas em `src/lumi/schemas/evals.py` para estruturar e validar formalmente os cenários de avaliação de RAG da Lumi, incluindo os enums `DatasetCategory` e `ExpectedBehavior`, o item individual `GoldenDatasetItem` e a coleção `GoldenDataset`.

#### Scenario: Categorias Válidas de Dataset
- **GIVEN** o enum `DatasetCategory`
- **THEN** deve conter os valores: `normative_standard`, `edge_case`, `norm_conflict`, `out_of_scope`, `jailbreak`.

#### Scenario: Comportamentos Esperados Válidos
- **GIVEN** o enum `ExpectedBehavior`
- **THEN** deve conter os valores: `grounded_answer`, `contingency_refusal`, `scope_refusal`, `injection_refusal`.

#### Scenario: Validação de Item do Golden Dataset
- **GIVEN** um item de avaliação com identificador `id`, `category`, `question`, `ground_truth_answer`, `expected_behavior`, `expected_sources`, `expected_sections` e `description`
- **WHEN** for instanciado como `GoldenDatasetItem`
- **THEN** o modelo DEVE validar que `id` segue o padrão `^GOLD-\d{2}$`, `question` e `ground_truth_answer` possuem conteúdo não vazio, e metadados estão preenchidos de forma coerente.

#### Scenario: Validação da Coleção GoldenDataset
- **GIVEN** um objeto contendo uma lista `items` de instâncias de `GoldenDatasetItem` e metadados como `version` e `description`
- **WHEN** for instanciado como `GoldenDataset`
- **THEN** o modelo DEVE validar todos os itens, verificar a unicidade de `id` entre os itens e expor métodos de agregação ou contagem por categoria.

### Requirement: Catálogo do Golden Dataset com 50 Cenários Normativos
O sistema DEVE fornecer o arquivo `tests/evals/golden_dataset.json` contendo exatamente 50 cenários técnicos reais, devidamente fundamentados nas normas `DIS-NOR-030` e `DIS-NOR-053` da Neoenergia Pernambuco, bem como nos guardrails de entrada.

#### Scenario: Distribuição Proporcional de Categorias
- **GIVEN** o arquivo `tests/evals/golden_dataset.json`
- **WHEN** o arquivo for carregado e parseado
- **THEN** a contagem total de itens DEVE ser exatamente 50;
- **AND** a categoria `normative_standard` DEVE conter exatamente 25 itens;
- **AND** a categoria `edge_case` DEVE conter exatamente 12 itens;
- **AND** a categoria `norm_conflict` DEVE conter exatamente 5 itens;
- **AND** a categoria `out_of_scope` DEVE conter exatamente 4 itens;
- **AND** a categoria `jailbreak` DEVE conter exatamente 4 itens.

#### Scenario: Conformidade dos Cenários de Segurança e Escopo
- **GIVEN** os itens de categoria `out_of_scope`
- **THEN** `expected_behavior` DEVE ser `scope_refusal` e `ground_truth_answer` DEVE corresponder à mensagem canônica `SCOPE_REJECTION_REASON` de `src/lumi/rag/guardrails.py`.
- **GIVEN** os itens de categoria `jailbreak`
- **THEN** `expected_behavior` DEVE ser `injection_refusal` e `ground_truth_answer` DEVE corresponder à mensagem canônica `INJECTION_REJECTION_REASON` de `src/lumi/rag/guardrails.py`.

### Requirement: Suíte de Testes de Integridade Estrutural
O sistema DEVE dispor de testes automatizados em `tests/unit/test_golden_dataset.py` para certificar que o arquivo JSON respeita integralmente o schema Pydantic e todas as regras de distribuição e unicidade.

#### Scenario: Execução dos Testes Unitários
- **WHEN** a suíte `pytest tests/unit/test_golden_dataset.py` for executada
- **THEN** todos os testes DEVEM passar com 100% de sucesso sem qualquer erro de validação.
