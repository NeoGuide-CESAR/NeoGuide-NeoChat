# Spec: RAG Prompts, Persona Lumi e Salvaguarda Normativa

## Requirements

### Requirement: Persona Lumi e Tom Didático
O sistema DEVE definir e utilizar instruções de sistema que instruam o modelo a adotar uma postura empática, instrutiva, acessível e objetiva, esclarecendo conceitos técnicos e desmistificando normas da Neoenergia Pernambuco sem uso de jargões desnecessários ou herméticos (RN-02).

#### Scenario: Orientação clara e sem jargões herméticos
- **GIVEN** uma consulta do usuário sobre terminologia ou regras das normas DIS-NOR-030 e DIS-NOR-053
- **WHEN** a instrução do sistema `LUMI_SYSTEM_PROMPT` for inspecionada ou aplicada
- **THEN** deve conter diretrizes explícitas instruindo o modelo a ser amigável, didático e explicar termos técnicos de forma compreensível.

### Requirement: Regra de Citação Enxuta e Obrigatória
O sistema DEVE exigir que toda resposta com afirmações técnicas baseadas nas normas contenha citação formal concisa e padronizada ao final no formato `[Fonte: <código_da_norma>, Item <seção>]` (ex.: `[Fonte: DIS-NOR-030, Item 5.2]`) (RF-03, RN-04).

#### Scenario: Formato padronizado de citação de fontes
- **GIVEN** a especificação do system prompt da Lumi
- **WHEN** o prompt mestre for avaliado para regras de citação
- **THEN** deve instruir a inclusão mandatória de citações enxutas ao final da resposta seguindo o padrão `[Fonte: <código_da_norma>, Item <seção>]`.

### Requirement: Separação de Responsabilidade e Delegação de Cálculos ao Wizard
O sistema DEVE proibir expressamente que a LLM execute cálculos finais absolutos de demanda ou dimensionamento elétrico, determinando que o assistente explique o método normativo, aponte fatores/tabelas aplicáveis e instrua o usuário a preencher e utilizar os campos do Wizard NeoGuide (RN-03).

#### Scenario: Consulta que solicita cálculo numérico final
- **GIVEN** uma solicitação do projetista pedindo para calcular valores de demanda ou cargas
- **WHEN** o modelo for guiado pelas diretrizes do prompt
- **THEN** o prompt deve vetar cálculos finais absolutos pela LLM e direcionar o cálculo exclusivamente para os campos do Wizard NeoGuide.

### Requirement: Salvaguarda de Imparcialidade Normativa
O sistema DEVE manter estrita neutralidade e imparcialidade técnica quando houver divergência, sobreposição ou ambiguidade entre as normas DIS-NOR-030 e DIS-NOR-053, apresentando ambas as abordagens com suas respectivas fontes e delegando a decisão técnica ao projetista.

#### Scenario: Ambiguidade ou conflito normativo entre DIS-NOR-030 e DIS-NOR-053
- **GIVEN** fragmentos normativos ou consultas que envolvam divergências entre a DIS-NOR-030 e a DIS-NOR-053
- **WHEN** a instrução mestre do prompt for formulada
- **THEN** deve determinar que a Lumi não escolha uma norma em detrimento da outra, expondo ambas as previsões e deixando a decisão técnica sob responsabilidade do profissional.

### Requirement: Mensagem Padronizada de Contingência por Ausência de Fontes
O sistema DEVE fornecer uma mensagem padronizada de contingência (`CONTINGENCY_NO_SOURCES_MESSAGE`) quando não forem encontrados documentos ou evidências relevantes acima do threshold de similaridade, orientando contato com canais formais da concessionária sem alucinações (RF-06).

#### Scenario: Consulta sem correspondência nas normas indexadas
- **GIVEN** ausência de fragmentos normativos no contexto recuperado
- **WHEN** a mensagem de contingência for invocada
- **THEN** deve retornar uma mensagem educada reconhecendo a ausência de base normativa nas normas indexadas e sugerindo consulta formal aos canais técnicos da Neoenergia.

### Requirement: Construtor do ChatPromptTemplate LangChain
O módulo `src/lumi/rag/prompts.py` DEVE disponibilizar uma função construtora `get_rag_prompt_template()` que retorne uma instância válida e funcional de `ChatPromptTemplate` contendo o prompt do sistema com suporte a injeção de `{context}`, histórico conversacional (`chat_history`) e mensagem do usuário (`{question}`).

#### Scenario: Instanciação do template de prompt para cadeia RAG
- **GIVEN** a função `get_rag_prompt_template()`
- **WHEN** a função for executada
- **THEN** deve retornar um `ChatPromptTemplate` do LangChain com variáveis de entrada para contexto documental, histórico e pergunta.
