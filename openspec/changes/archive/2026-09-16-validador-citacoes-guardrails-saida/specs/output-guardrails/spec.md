# Spec: Guardrails de Saída e Validador de Citações (Output Guardrails)

## Requirements

### Requirement: Extração Determinística de Citações Normativas
O sistema DEVE extrair com baixa latência e de forma puramente determinística todas as citações normativas presentes no texto de resposta gerado pelo modelo, capturando o código do documento normativo e a seção/item/tabela referenciada (ex.: `[Fonte: DIS-NOR-030, Item 5.3]`).

#### Scenario: Extração de Citação Padrão com Código e Seção
- **GIVEN** o texto "O limite admissível é de 5% [Fonte: DIS-NOR-030, Item 5.2]."
- **WHEN** a função `extract_citations` for executada
- **THEN** a lista retornada DEVE conter a tupla `("DIS-NOR-030", "Item 5.2")`.

#### Scenario: Extração de Citação com Paginação Adicional
- **GIVEN** o texto "Conforme a norma [Fonte: DIS-NOR-030, Item 5.3, Pág. 28], a edificação coletiva..."
- **WHEN** a função `extract_citations` for executada
- **THEN** a função DEVE extrair a tupla `("DIS-NOR-030", "Item 5.3")`, higienizando a paginação.

#### Scenario: Extração Múltipla de Normas Diferentes
- **GIVEN** uma resposta que referencia duas normas: "Veja [Fonte: DIS-NOR-030, Item 5.1] e também [Fonte: DIS-NOR-053, Item 6.2]."
- **WHEN** a função `extract_citations` for executada
- **THEN** a lista retornada DEVE conter `("DIS-NOR-030", "Item 5.1")` e `("DIS-NOR-053", "Item 6.2")`.

#### Scenario: Texto sem Citações Normativas
- **GIVEN** uma resposta conversacional simples "Olá! Como posso ajudar você hoje?"
- **WHEN** a função `extract_citations` for executada
- **THEN** a lista retornada DEVE ser vazia `[]`.

---

### Requirement: Detecção de Salvaguarda de Cálculo Numérico (RN-03)
O sistema DEVE detectar quando o assistente emite conclusões ou resultados numéricos absolutos de cálculo de demanda ou dimensionamento elétrico (kVA, kW, amperes) sem orientar explicitamente o usuário a recorrer aos campos do Wizard NeoGuide.

#### Scenario: Violação de Cálculo Absoluto sem Menção ao Wizard NeoGuide
- **GIVEN** o texto "A demanda total calculada para seu prédio é de exatos 142,5 kVA."
- **WHEN** a função `check_calculation_safeguard` for executada
- **THEN** a função DEVE retornar `True` (violação detectada).

#### Scenario: Cálculo Acompanhado de Orientação ao Wizard NeoGuide
- **GIVEN** o texto "A demanda estimada preliminar resulta em 142 kVA. Contudo, para homologar a memória oficial, utilize os campos de cálculo do Wizard NeoGuide."
- **WHEN** a função `check_calculation_safeguard` for executada
- **THEN** a função DEVE retornar `False` (sem violação, pois há menção e direcionamento explícito ao Wizard NeoGuide).

#### Scenario: Explicação Normativa Sem Conclusão Numérica Absoluta
- **GIVEN** o texto "Para 40 apartamentos, consulte a Tabela 4 da DIS-NOR-030 e aplique os fatores de simultaneidade correspondentes."
- **WHEN** a função `check_calculation_safeguard` for executada
- **THEN** a função DEVE retornar `False`.

---

### Requirement: Validação Cruzada de Saída e Detecção de Alucinações
O sistema DEVE comparar as citações extraídas da resposta com os fragmentos (`RetrievedChunk`) retornados pelo retriever/reranker. Caso uma citação aponte norma ou seção inexistente no contexto recuperado, deve marcá-la como alucinação e classificar a saída com flag de advertência.

#### Scenario: Resposta com Citações 100% Fundamentadas no Contexto
- **GIVEN** fragmentos recuperados contendo `DIS-NOR-030` na seção `Item 5.2`
- **AND** a resposta textual citando `[Fonte: DIS-NOR-030, Item 5.2]`
- **WHEN** `validate_output` for executada
- **THEN** `is_valid` DEVE ser `True`, `valid_citations` DEVE conter a citação, `hallucinated_citations` DEVE ser vazia e `warning_flags` DEVE ser vazia.

#### Scenario: Citação com Seção Inexistente nos Fragmentos (Alucinação)
- **GIVEN** fragmentos recuperados contendo apenas a seção `Item 5.2` da `DIS-NOR-030`
- **AND** a resposta textual citando `[Fonte: DIS-NOR-030, Item 99.4]`
- **WHEN** `validate_output` for executada
- **THEN** `is_valid` DEVE ser `False`, `hallucinated_citations` DEVE conter a citação inválida e `warning_flags` DEVE conter `"HALLUCINATED_CITATION"`.

#### Scenario: Citação com Norma Não Recuperada (Alucinação)
- **GIVEN** fragmentos recuperados contendo apenas a norma `DIS-NOR-030`
- **AND** a resposta textual citando `[Fonte: DIS-NOR-999, Item 1.0]`
- **WHEN** `validate_output` for executada
- **THEN** `is_valid` DEVE ser `False` e `hallucinated_citations` DEVE conter a citação.

---

### Requirement: Auditoria Assíncrona e Telemetria em Background (ADR-04)
A validação de saída DEVE ser executada de forma desacoplada no worker em segundo plano (`persist_interaction_background`), emitindo alerta de log em caso de inconformidade e enriquecendo os metadados da mensagem persistida.

#### Scenario: Execução em Background com Violação Detectada
- **GIVEN** uma resposta gerada contendo citação alucinada ou violação de cálculo
- **WHEN** o worker `persist_interaction_background` for acionado
- **THEN** o worker DEVE invocar `validate_output`, emitir log `logger.warning("output_guardrail_violation", ...)` com as flags e persistir a mensagem com `audit_flags` gravadas nos metadados.
