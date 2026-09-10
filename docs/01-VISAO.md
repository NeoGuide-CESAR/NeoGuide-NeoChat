# 01. Visão do Projeto — Lumi (Módulo NeoGuide)

## 1. Contexto & Origem

No ecossistema de distribuição de energia elétrica de Pernambuco, a **Neoenergia Pernambuco** (integrante do Grupo Neoenergia / Iberdrola) recebe anualmente cerca de **1.400 projetos elétricos** de edificações com múltiplas unidades consumidoras.

Historicamente, aproximadamente **50% desses projetos são reprovados** em sua primeira análise técnica. As causas raízes desse gargalo envolvem:
- Elevada complexidade normativa e dispersão de parâmetros em diversas normas técnicas corporativas (em especial **DIS-NOR-030** e **DIS-NOR-053**);
- Erros de interpretação em fatores de demanda, tabelas de dimensionamento e cálculo de cargas especiais;
- Grande retrabalho para projetistas e engenheiros analistas da concessionária, dilatando os prazos de ligação de novas edificações.

Como resposta a esse desafio acadêmico e de mercado (CESAR School - 3º Período), o time concebeu o ecossistema **NeoGuide**, uma plataforma com wizard interativo para guiar o projetista no memorial de cálculo de demanda.

Dentro dessa solução, a **Lumi** é o **módulo conversacional especialista com Retrieval-Augmented Generation (RAG)**, responsável por sanar dúvidas normativas de engenharia em tempo real.

---

## 2. Declaração de Visão do Produto

> **Para** projetistas e engenheiros eletricistas que elaboram projetos de entrada de energia e memoriais de cálculo de múltiplas unidades consumidoras,  
> **O Lumi** é um serviço backend conversacional inteligente baseado em RAG,  
> **Que** esclarece dúvidas normativas em tempo hábil, interpreta tabelas e orienta cálculos com precisão baseada estritamente nas normas oficiais da Neoenergia Pernambuco,  
> **Diferente de** buscar manualmente em PDFs de centenas de páginas ou consultar LLMs genéricas propensas a alucinações técnicas,  
> **O nosso produto** fornece respostas instrutivas, amigáveis, fundamentadas e acompanhadas de metadados precisos com citação de norma, seção e página.

---

## 3. Proposta de Valor

1. **Acurácia Normativa sem Alucinação:** Indexação semântica e chunking focado nas normas proprietárias da Neoenergia (ex.: tabelas de demanda, fatores de simultaneidade, tipos de fornecimento).
2. **Respostas Amigáveis e Instrutivas:** Tom didático que explica o *porquê* técnico sem linguagem excessivamente árida.
3. **Citações Limpas com Metadados Ricos:** Resposta textual fluida com citações curtas, acompanhada de metadados estruturados no payload da API (norma, capítulo, tabela, página e score de similaridade).
4. **Desacoplamento e Interoperabilidade:** Backend headless em Python que atende perfeitamente ao frontend do assistente NeoGuide, mas também pode ser plugado em portais corporativos, WhatsApp ou canais internos.

---

## 4. Stakeholders & Perfis de Usuário

| Stakeholder / Ator | Descrição | Valor Percebido |
| :--- | :--- | :--- |
| **Projetista Elétrico (Usuário Final indireto)** | Engenheiro civil/eletricista ou técnico projetista que alimenta o memorial de cálculo. | Rapidez para tirar dúvidas pontuais sem interromper o fluxo do cálculo; redução drástica de reprovações. |
| **Frontend do Wizard NeoGuide (Cliente da API)** | Aplicação web interativa que coleta dados do memorial e exibe a interface de chat. | API consistente (SSE/Streaming ou REST) com metadados de fontes separados para renderizar cards de referência. |
| **Analista Técnico da Concessionária** | Equipe de homologação da Neoenergia. | Recebimento de memoriais padronizados e em conformidade com as normas vigentes. |
| **Equipe de Manutenção / Curadoria de IA** | Desenvolvedores do time acadêmico. | Pipeline de ingestão simples para atualizar normas quando houver novas revisões (ex.: REV07 -> REV08). |

---

## 5. Limites e Não-Objetivos (Out of Scope)

Para manter o foco e garantir entrega de alta qualidade:

- **Não faz os cálculos numéricos pelo usuário:** A responsabilidade de orquestrar a lógica matemática do memorial pertence ao módulo Wizard do NeoGuide; a Lumi atua como consultora técnica normativa e guia de interpretação.
- **Não possui interface gráfica própria acoplada:** A Lumi é um serviço de backend com endpoints de API (REST/Streaming). Um playground simples (ex.: Swagger/FastAPI docs) existe apenas para fins de teste e desenvolvimento.
- **Não altera normas:** O sistema não infere regras que não estejam explicitamente cobertas no material de referência indexado. Em caso de ausência normativa, deve declarar explicitamente a limitação e orientar contato formal com a concessionária.
- **Não prioriza uma norma sobre outra:** Em caso de conflito ou divergência entre a DIS-NOR-030 e a DIS-NOR-053, a Lumi deve apresentar ambas as versões com suas respectivas citações estruturadas, deixando o projetista tomar a decisão técnica final. O sistema atua como consultora imparcial, não como decisora normativa.

---

## 6. Critérios de Sucesso do Projeto

1. **Redução do Tempo de Resolução de Dúvidas:** Obter a resposta e citação correta em menos de 3 segundos.
2. **Precisão nas Fontes:** Pelo menos 90% das respostas com referências corretas à norma (DIS-NOR-030 / DIS-NOR-053), item e página.
3. **Facilidade de Integração:** Disponibilização de contrato de API REST/Streaming claro com separação limpa de texto de resposta e metadados de fontes.
