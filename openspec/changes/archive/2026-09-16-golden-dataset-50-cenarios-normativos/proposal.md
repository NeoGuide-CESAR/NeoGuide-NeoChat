# Proposal: Golden Dataset de Avaliação de RAG com 50 Cenários Normativos

## Contexto
O assistente técnico especializado **Lumi NeoGuide** foi projetado para atuar no domínio crítico de engenharia elétrica de baixa e média tensão da **Neoenergia Pernambuco** (normas técnicas **DIS-NOR-030** e **DIS-NOR-053**). Em sistemas de missão crítica, desvios normativos ou alucinações de cálculo e interpretação de normas acarretam reprovações de projetos, riscos elétricos graves ou custos indevidos.

Para garantir confiabilidade, segurança e anti-alucinação na esteira de IA, é indispensável estabelecer um **Golden Dataset de Avaliação de RAG** representativo e curado, com validação estrutural estrita por modelos Pydantic e cobertura balanceada de cenários do mundo real.

## Justificativa
1. **Padronização e Integridade com Pydantic:** Estruturar `DatasetCategory` (categorias de avaliação), `ExpectedBehavior` (comportamentos esperados) e modelos `GoldenDatasetItem` e `GoldenDataset` assegura tipagem forte e validação contínua contra corrupção de schema.
2. **Distribuição Realista e Equilibrada de Casos de Teste (50 Cenários):**
   - **25 Normative Standard (`normative_standard`):** Cenários centrais de aplicação direta das normas DIS-NOR-030 e DIS-NOR-053 (fatores de demanda residencial e comercial, dimensionamento de ramal, caixas de medição, cubículos, etc.).
   - **12 Edge Case (`edge_case`):** Situações limítrofes e complexas (edificações mistas, recarga veicular, bombas de incêndio em paralelo, vãos máximos de telecom, cubículos compactos).
   - **5 Norm Conflict (`norm_conflict`):** Ambiguidade ou aparente conflito entre versões/normas (ex.: DIS-NOR-030 vs DIS-NOR-053 para agrupamentos e transição aéreo-subterrâneo), exigindo discernimento fundamentado do assistente.
   - **4 Out of Scope (`out_of_scope`):** Perguntas desconexas (culinária, esportes, astrologia) testando a recusa canônica por guardrail de escopo.
   - **4 Jailbreak (`jailbreak`):** Tentativas ativas de prompt injection, modo DAN, sobrescrita de persona e extração de system prompt testando o bloqueio canônico por guardrail de segurança.
3. **Respostas Canônicas Alinhadas aos Guardrails:** Casos fora de escopo e de jailbreak devem incorporar textualmente as mensagens padrão de recusa definidas em `src/lumi/rag/guardrails.py`.
4. **Alinhamento com a Documentação e Governança:** Atualizar a seção 4.1 de `docs/07-SEGURANCA-E-AVALIACAO-IA.md` documentando o schema Pydantic e a taxonomia do dataset.

## Escopo

### In-Scope
- Criação dos schemas Pydantic em `src/lumi/schemas/evals.py`:
  - Enums `DatasetCategory` e `ExpectedBehavior`.
  - Modelos `GoldenDatasetItem` e `GoldenDataset` com validação de campos obrigatórios, IDs (regex `^GOLD-\d{2}$`) e metadados.
  - Exportação em `src/lumi/schemas/__init__.py`.
- Criação do dataset `tests/evals/golden_dataset.json` com exatamente 50 cenários técnicos reais numerados de `GOLD-01` a `GOLD-50`:
  - 25 `normative_standard`
  - 12 `edge_case`
  - 5 `norm_conflict`
  - 4 `out_of_scope`
  - 4 `jailbreak`
- Criação de suíte de testes de integridade em `tests/unit/test_golden_dataset.py` validando:
  - Validação de schema Pydantic sem erro;
  - Exatamente 50 itens;
  - Unicidade estrita dos IDs;
  - Contagem exata por categoria;
  - Formato de IDs (`GOLD-01` a `GOLD-50`);
  - Ground truth canônico para out_of_scope e jailbreak.
- Atualização da Seção 4.1 de `docs/07-SEGURANCA-E-AVALIACAO-IA.md`.
- Sincronização e arquivamento no padrão OpenSpec SDD.

### Out-of-Scope
- Execução de avaliações LLM-as-a-Judge com chamadas a APIs pagas (Gemini/Claude) durante o teste unitário (isso faz parte da esteira manual/CI de evals com Ragas).
- Alteração da lógica de runtime de busca ou streaming do chat.
