# Proposal: Prompts, Persona Lumi e Salvaguarda de Imparcialidade Normativa

## Context
A Lumi (NeoGuide) é um serviço conversacional de engenharia elétrica e telecomunicações baseado em RAG para apoiar projetistas de edificações com múltiplas unidades consumidoras atendidas pela Neoenergia Pernambuco. Para evitar erros graves de projeto, super ou subdimensionamento de condutores e transformadores, e reprovações nos memoriais de cálculo, a Lumi necessita de diretrizes de sistema (System Prompts) rigorosamente estruturadas, alinhadas à sua persona didática e às salvaguardas de conformidade normativa e segurança de IA.

## Motivation & Value
A comunicação da Lumi deve ser acolhedora, amigável e instrutiva (RN-02), desmistificando o labirinto normativo sem recorrer a jargões inacessíveis. Ao mesmo tempo, respostas de engenharia exigem precisão absoluta:
1. Toda afirmação técnica deve citar formalmente a norma e o item de forma enxuta e limpa ao final (RF-03, RN-04).
2. A LLM não deve fazer contas numéricas finais ou assumir valores absolutos de demanda, orientando o usuário a preencher os campos do Wizard NeoGuide (RN-03).
3. Havendo divergência ou ambiguidade entre as normas DIS-NOR-030 e DIS-NOR-053, o sistema deve manter imparcialidade técnica, apresentando os dois critérios e delegando a decisão ao engenheiro responsável.
4. Na falta de evidências documentais nos fragmentos recuperados, deve emitir uma resposta de contingência transparente e segura (RF-06).

## Scope
### In-Scope
- Criação de `src/lumi/rag/prompts.py` contendo:
  - `LUMI_SYSTEM_PROMPT`: instrução de sistema que estabelece persona, tom, regras de citação, delegação de cálculo e imparcialidade normativa.
  - `CONTINGENCY_NO_SOURCES_MESSAGE` (e alias `CONTINGENCY_NO_SOURCES_PROMPT`): mensagem padronizada de recusa instrutiva quando não houver contexto documental com similaridade suficiente.
  - `get_rag_prompt_template()`: fábrica de `ChatPromptTemplate` do LangChain com injeção de contexto documental, histórico de mensagens e pergunta do usuário.
- Exportação dos componentes em `src/lumi/rag/__init__.py`.
- Desenvolvimento guiado por testes (TDD) em `tests/unit/test_prompts.py`.

### Out-of-Scope
- Ingestão e indexação vetorial no PostgreSQL/pgvector (escopo de FEAT-06 e FEAT-07).
- Orquestração completa da cadeia RAG e invocação de LLMs (Google Gemini / Anthropic Claude) (escopo de FEAT-07 e FEAT-12).
- Endpoints HTTP REST/SSE na API FastAPI (escopo de FEAT-08).
