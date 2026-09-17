# Proposal: Validador Assíncrono de Citações e Guardrails de Saída via BackgroundTasks

## Context
A Lumi (NeoGuide) é a assistente virtual especializada nas normas técnicas da Neoenergia Pernambuco (DIS-NOR-030 e DIS-NOR-053).
Para garantir a confiabilidade técnica nas respostas sobre infraestrutura elétrica e compartilhamento de rede, o sistema já conta com guardrails de entrada (detecção de prompt injection e sanitização de PII) e guardrails de recuperação (threshold de similaridade cosseno no pgvector e contingência).

No entanto, modelos de linguagem generativos podem cometer alucinações factuais no momento da síntese textual — como inventar números de itens inexistentes (ex.: "Item 99.4") ou citar normas não recuperadas no contexto. Além disso, de acordo com a regra de negócio RN-03, a Lumi não deve realizar cálculos numéricos absolutos de demanda ou dimensionamento elétrico, devendo sempre direcionar o usuário aos campos dedicados do Wizard NeoGuide.

## Motivation & Value
A implementação dos Guardrails de Saída (Output Guardrails) completa a arquitetura de defesa em profundidade (Defense-in-Depth) definida em `docs/07-SEGURANCA-E-AVALIACAO-IA.md` (Seção 2.3):
1. **Auditoria Determinística de Citações:** Validação de referências textuais (ex.: `[Fonte: DIS-NOR-030, Item 5.3]`) contra os metadados dos fragmentos (`RetrievedChunk`) efetivamente retornados pelo banco vetorial.
2. **Salvaguarda de Cálculo (RN-03):** Detecção de emissão de valores numéricos finais de demanda (kVA, kW, A) sem a necessária orientação de cálculo e direcionamento ao Wizard NeoGuide.
3. **Execução Assíncrona e Latência Zero (ADR-04):** A validação de saída é executada no worker assíncrono em segundo plano (`persist_interaction_background`), sem acrescentar qualquer milissegundo de latência perceptível ao streaming SSE ou resposta síncrona ao usuário.
4. **Observabilidade e Auditoria Contínua:** Emissão de alertas estruturados (`logger.warning("output_guardrail_violation", ...)`) com as flags de auditoria e citações inválidas, enriquecendo o registro para rastreabilidade técnica.

## Scope

### In-Scope
- Criação do módulo `src/lumi/rag/output_guardrails.py`:
  - Dataclass imutável `OutputGuardrailResult`: `is_valid: bool`, `valid_citations: list[str]`, `hallucinated_citations: list[str]`, `has_calculation_violation: bool`, `warning_flags: list[str]`.
  - `extract_citations(text: str) -> list[tuple[str, str]]`: regex determinístico rápido para captura de referências a normas e seções (ex.: `[Fonte: DIS-NOR-030, Item 5.3]`).
  - `check_calculation_safeguard(text: str) -> bool`: detecção de conclusões numéricas absolutas de demanda/dimensionamento desacompanhadas de menção ao Wizard NeoGuide (RN-03).
  - `validate_output(response_text: str, retrieved_chunks: list[RetrievedChunk] | list[dict[str, Any]] | None) -> OutputGuardrailResult`: cruzamento determinístico entre citações no texto e fragmentos recuperados.
- Integração em `src/lumi/services/analytics_service.py` (`persist_interaction_background`):
  - Execução assíncrona não-bloqueante pós-resposta.
  - Logging estruturado de advertência (`logger.warning("output_guardrail_violation", ...)`) com detalhes das violações.
  - Gravação de `audit_flags` nos metadados da mensagem persistida.
- Exposição das estruturas e funções em `src/lumi/rag/__init__.py`.
- Testes unitários completos em `tests/unit/test_output_guardrails.py` e testes de integração em `tests/integration/test_output_audit_background.py`.

### Out-of-Scope
- Bloqueio síncrono ou interrupção do stream SSE para reescrita por LLM-as-a-Judge (custo e latência proibitivos para o MVP).
- Modificação DDL no schema de tabelas relacionais do banco.
