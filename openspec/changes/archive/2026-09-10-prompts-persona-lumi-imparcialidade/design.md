# Design: Prompts, Persona Lumi e Salvaguarda de Imparcialidade Normativa

## Architecture & Layout
O módulo `src/lumi/rag/prompts.py` é responsável pela engenharia de prompts da Lumi, fornecendo os textos mestres de instrução do sistema (System Prompt), regras estritas de conduta, contingência e templates compatíveis com o ecossistema LangChain (`ChatPromptTemplate`).

### Componentes Principais

```
src/lumi/rag/
├── __init__.py          # Exporta LUMI_SYSTEM_PROMPT, CONTINGENCY_NO_SOURCES_MESSAGE, get_rag_prompt_template
└── prompts.py           # Definição das constantes de prompt e construtor ChatPromptTemplate
```

1. **`LUMI_SYSTEM_PROMPT`**:
   - **Identidade e Persona (RN-02)**: Apresenta a Lumi como assistente especialista em normas técnicas da Neoenergia Pernambuco, com tom amigável, empático, didático e acolhedor, evitando jargões técnicos indecifráveis e explicando-os com clareza.
   - **Contexto Normativo Base**: Seção dedicada para injeção de fragmentos normativos recuperados via `{context}`.
   - **Diretriz de Citação Enxuta (RF-03, RN-04)**: Determina a inclusão mandante de referências concisas ao final das respostas técnicas no formato padronizado `[Fonte: <código_da_norma>, Item <seção>]` (ex.: `[Fonte: DIS-NOR-030, Item 5.2]`).
   - **Delegação de Cálculos Matemáticos (RN-03)**: Veta a execução de cálculos finais absolutos de demanda ou carga pela LLM. Instruem a explicação do método de cálculo, fatores de simultaneidade e tabelas cabíveis, direcionando o projetista para a utilização dos campos do Wizard do NeoGuide.
   - **Salvaguarda de Imparcialidade Normativa**: Orienta que, havendo discrepâncias, divergências ou ambiguidades entre a DIS-NOR-030 e a DIS-NOR-053, o assistente nunca deve escolher uma norma unilateralmente; deve expor ambas as alternativas fundamentadas e delegar a decisão técnica ao projetista.
   - **Salvaguarda Anti-Alucinação (RF-06)**: Instrução de que o assistente não deve inventar dados ou extrapolar informações não comprovadas pelo contexto documental.

2. **`CONTINGENCY_NO_SOURCES_MESSAGE` / `CONTINGENCY_NO_SOURCES_PROMPT`**:
   - Mensagem oficial padronizada para retorno direto ou uso em fallback caso a recuperação vetorial retorne zero evidências ou evidências com score abaixo do limiar:
   > *"Não localizei essa informação específica nas normas DIS-NOR-030 ou DIS-NOR-053 indexadas. Para este caso particular, recomendo consultar formalmente o canal de atendimento técnico de projetos da Neoenergia."*

3. **`get_rag_prompt_template(system_prompt: str | None = None) -> ChatPromptTemplate`**:
   - Constrói e retorna um `ChatPromptTemplate` composto por:
     - `SystemMessagePromptTemplate` contendo o `LUMI_SYSTEM_PROMPT` (com interpolação de `{context}`).
     - `MessagesPlaceholder(variable_name="chat_history", optional=True)` para histórico de turnos anteriores.
     - `HumanMessagePromptTemplate` contendo a pergunta do usuário (`{question}`).
   - Fornece também alias `get_chat_prompt_template = get_rag_prompt_template` para garantir interoperabilidade total com os nomes referenciados no roadmap.

## Tooling & Typing
- Compatibilidade estrita com `langchain_core.prompts.ChatPromptTemplate` e `MessagesPlaceholder`.
- Tipagem estrita com anotações completas (`str`, `ChatPromptTemplate`, `list[str]`) para aprovação no `mypy`.
- Conformidade integral com formatação e linting do `ruff`.
