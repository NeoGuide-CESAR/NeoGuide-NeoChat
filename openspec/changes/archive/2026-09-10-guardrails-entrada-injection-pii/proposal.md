# Proposal: Guardrails de Entrada contra Prompt Injection e Sanitização de PII

## Context
O Lumi (NeoGuide) é um assistente normativo inteligente para infraestrutura de telecomunicações e redes de distribuição elétrica da Neoenergia Pernambuco (DIS-NOR-030 e DIS-NOR-053). Os usuários do sistema são engenheiros, projetistas e técnicos que submetem consultas sobre cálculo de demanda, compartilhamento de postes, subestações e diretrizes técnicas.

No ecossistema de LLMs aplicadas a domínios de missão crítica, a camada de orquestração RAG precisa proteger tanto a integridade do assistente quanto a privacidade dos dados submetidos pelo projetista antes que qualquer chamada externa de embeddings ou LLM seja executada.

## Motivation & Value
A implementação de Guardrails de Entrada (Input Guardrails) estabelece a primeira linha de defesa da arquitetura em profundidade (Defense-in-Depth) definida em `docs/07-SEGURANCA-E-AVALIACAO-IA.md`:
1. **Proteção contra Prompt Injection e Jailbreaks:** Impede que atacantes ou comandos maliciosos manipulem as instruções do sistema ("jailbreaks", "DAN mode", "ignore previous instructions", "system override"), garantindo que o assistente permaneça dentro de sua persona segura e diretrizes normativas.
2. **Conformidade com a LGPD e Sanitização de PII:** Projetistas podem acidentalmente colar documentos com dados sensíveis de clientes. A detecção e mascaramento imediato de CPFs, CNPJs e Contas Contrato/faturamento substitui dados reais por marcadores seguros (`[CPF_REMOVIDO]`, `[CNPJ_REMOVIDO]`, `[CONTA_CONTRATO_REMOVIDA]`) antes da persistência ou envio para modelos de linguagem.
3. **Filtro de Escopo Temático (Foco Normativo):** Evita consumo desnecessário de tokens e alucinações recusando educadamente perguntas sobre temas totalmente alheios à engenharia elétrica e normas (receitas, futebol, horóscopo).
4. **Zero Latência de Rede:** Toda a validação opera de maneira puramente determinística em memória via expressões regulares otimizadas e compiladas, sem dependência de APIs externas ou LLM-as-a-Judge na camada de entrada.

## Scope

### In-Scope
- Criação do módulo `src/lumi/rag/guardrails.py` e exposição no pacote `src/lumi/rag/__init__.py`.
- Modelo de dados estruturado `GuardrailResult` contendo:
  - `is_allowed: bool`
  - `sanitized_text: str`
  - `rejection_reason: str | None`
  - `detected_pii: list[str]`
  - `is_injection: bool`
- Detecção determinística de padrões de Prompt Injection e Jailbreak (multilíngue pt-BR/en-US, case-insensitive e tolerante a acentuação).
- Sanitização determinística de PII brasileiro:
  - CPF formatado (`123.456.789-00`) e desformatado (`11` dígitos numéricos contínuos).
  - CNPJ formatado (`12.345.678/0001-90`) e desformatado (`14` dígitos numéricos contínuos).
  - Conta contrato e identificadores de documento de faturamento (`[CONTA_CONTRATO_REMOVIDA]`).
- Verificação de escopo temático com recusa educada para tópicos flagrantemente não relacionados (receitas, futebol, horóscopo), preservando saudações e dúvidas técnicas elétricas/normativas.
- Função orquestradora `validate_input(text: str) -> GuardrailResult`.
- Suíte abrangente de testes unitários em `tests/unit/test_guardrails.py` seguindo a metodologia TDD (Red-Green-Refactor).

### Out-of-Scope
- Guardrails de recuperação semântica (threshold de similaridade cosseno no pgvector — tratado em task subsequente do pipeline RAG).
- Guardrails de saída (validação pós-stream de citações normativas e verificação factual Ragas).
- Treinamento ou fine-tuning de classificadores neurais de toxicidade.
