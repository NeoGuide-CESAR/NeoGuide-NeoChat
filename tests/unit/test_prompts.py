"""Testes unitários para os templates de prompt, persona Lumi e salvaguardas normativas."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from lumi.rag.prompts import (
    CONTINGENCY_NO_SOURCES_MESSAGE,
    CONTINGENCY_NO_SOURCES_PROMPT,
    LUMI_SYSTEM_PROMPT,
    get_chat_prompt_template,
    get_rag_prompt_template,
)


class TestLumiSystemPrompt:
    """Validação das regras de negócio e diretrizes do System Prompt mestre."""

    def test_persona_friendly_and_instructional(self) -> None:
        """Valida que o prompt define tom amigável, empático, instrutivo e sem jargões (RN-02)."""
        prompt_lower = LUMI_SYSTEM_PROMPT.lower()

        assert "lumi" in prompt_lower
        assert "amigável" in prompt_lower or "amigavel" in prompt_lower
        assert "didátic" in prompt_lower or "didatic" in prompt_lower or "instrutiv" in prompt_lower
        assert "jarg" in prompt_lower
        assert "neoenergia" in prompt_lower

    def test_citation_rule_lean_and_mandatory(self) -> None:
        """Valida regra de citação enxuta no formato [Fonte: DIS-NOR-030, Item 5.2] (RF-03, RN-04)."""
        prompt = LUMI_SYSTEM_PROMPT

        assert "[Fonte:" in prompt
        assert "Item" in prompt
        assert "DIS-NOR-030" in prompt or "<código_da_norma>" in prompt or "<norma>" in prompt

        # Deve explicitar a obrigatoriedade de citar ao final ou fundamentar respostas técnicas
        prompt_lower = prompt.lower()
        assert "citação" in prompt_lower or "citacao" in prompt_lower
        assert "final" in prompt_lower or "fonte" in prompt_lower

    def test_calculation_separation_wizard_neoguide(self) -> None:
        """Valida a separação de responsabilidade de cálculo direcionando ao Wizard NeoGuide (RN-03)."""
        prompt = LUMI_SYSTEM_PROMPT
        prompt_lower = prompt.lower()

        assert "wizard" in prompt_lower
        assert "neoguide" in prompt_lower

        # Proibição explícita de cálculo final absoluto pela LLM
        assert (
            "não realize o cálculo final" in prompt_lower
            or "não calcule" in prompt_lower
            or "não realize cálculos" in prompt_lower
            or "nao realize o calculo" in prompt_lower
            or "proibido" in prompt_lower
            or "não deve assumir" in prompt_lower
        )

    def test_normative_impartiality_dis_nor_030_vs_053(self) -> None:
        """Valida a salvaguarda de imparcialidade em divergências entre DIS-NOR-030 e DIS-NOR-053."""
        prompt = LUMI_SYSTEM_PROMPT

        assert "DIS-NOR-030" in prompt
        assert "DIS-NOR-053" in prompt

        prompt_lower = prompt.lower()
        assert (
            "imparcial" in prompt_lower
            or "imparcialidade" in prompt_lower
            or "divergência" in prompt_lower
            or "divergencia" in prompt_lower
        )
        assert (
            "projetista" in prompt_lower or "decisão" in prompt_lower or "decisao" in prompt_lower
        )

    def test_context_placeholder_in_system_prompt(self) -> None:
        """Valida que o prompt de sistema contém placeholder {context} para injeção documental."""
        assert "{context}" in LUMI_SYSTEM_PROMPT


class TestContingencyMessage:
    """Validação da mensagem padronizada de contingência por ausência de fontes."""

    def test_contingency_no_sources_message_content(self) -> None:
        """Valida conteúdo e tom da resposta padronizada sem fontes (RF-06)."""
        assert isinstance(CONTINGENCY_NO_SOURCES_MESSAGE, str)
        assert len(CONTINGENCY_NO_SOURCES_MESSAGE) > 30

        message_lower = CONTINGENCY_NO_SOURCES_MESSAGE.lower()
        assert "dis-nor-030" in message_lower
        assert "dis-nor-053" in message_lower
        assert "neoenergia" in message_lower
        assert (
            "canal" in message_lower or "atendimento" in message_lower or "formal" in message_lower
        )

    def test_contingency_prompt_alias(self) -> None:
        """Valida que CONTINGENCY_NO_SOURCES_PROMPT é alias para CONTINGENCY_NO_SOURCES_MESSAGE."""
        assert CONTINGENCY_NO_SOURCES_PROMPT == CONTINGENCY_NO_SOURCES_MESSAGE


class TestGetRagPromptTemplate:
    """Validação da construção de ChatPromptTemplate do LangChain."""

    def test_get_rag_prompt_template_returns_chat_prompt_template(self) -> None:
        """Valida que get_rag_prompt_template() retorna instância válida de ChatPromptTemplate."""
        prompt_template = get_rag_prompt_template()

        assert isinstance(prompt_template, ChatPromptTemplate)

    def test_prompt_template_messages_structure(self) -> None:
        """Valida componentes do template: system com context, MessagesPlaceholder e human."""
        prompt_template = get_rag_prompt_template()

        # Deve conter pelo menos 3 mensagens no template (system, placeholder do chat_history, human)
        messages = prompt_template.messages
        assert len(messages) >= 3

        # O primeiro elemento é a instrução de sistema
        assert hasattr(messages[0], "prompt") or hasattr(messages[0], "template")

        # Deve conter um MessagesPlaceholder para chat_history
        placeholder_exists = any(
            isinstance(m, MessagesPlaceholder) and m.variable_name == "chat_history"
            for m in messages
        )
        assert placeholder_exists, (
            "MessagesPlaceholder com variable_name='chat_history' é obrigatório"
        )

    def test_prompt_template_formatting_without_history(self) -> None:
        """Valida formatação do prompt com context e question sem histórico prévio."""
        prompt_template = get_rag_prompt_template()

        formatted = prompt_template.format_messages(
            context="[DIS-NOR-030 Item 5.2] Condutores devem ser dimensionados conforme tabela 3.",
            question="Como dimensionar os condutores de entrada?",
        )

        assert isinstance(formatted, list)
        assert all(isinstance(m, BaseMessage) for m in formatted)
        assert len(formatted) >= 2

        system_message = formatted[0]
        assert isinstance(system_message, SystemMessage)
        assert "Condutores devem ser dimensionados conforme tabela 3." in system_message.content
        assert (
            "[Fonte: DIS-NOR-030, Item 5.2]" in system_message.content
            or "[Fonte:" in system_message.content
        )

        human_message = formatted[-1]
        assert isinstance(human_message, HumanMessage)
        assert human_message.content == "Como dimensionar os condutores de entrada?"

    def test_prompt_template_formatting_with_chat_history(self) -> None:
        """Valida formatação do prompt preservando a sequência de turnos conversacionais."""
        prompt_template = get_rag_prompt_template()

        history = [
            HumanMessage(content="Olá, você conhece a DIS-NOR-030?"),
            AIMessage(content="Olá! Sim, conheço as normas técnicas da Neoenergia."),
        ]

        formatted = prompt_template.format_messages(
            context="[DIS-NOR-030 Item 4.1] Tensão de fornecimento 380/220V.",
            question="Qual o fator de potência de referência?",
            chat_history=history,
        )

        assert len(formatted) == 4
        assert isinstance(formatted[0], SystemMessage)
        assert formatted[1] == history[0]
        assert formatted[2] == history[1]
        assert isinstance(formatted[3], HumanMessage)
        assert formatted[3].content == "Qual o fator de potência de referência?"

    def test_custom_system_prompt_override(self) -> None:
        """Valida que é possível customizar o system prompt mantendo a injeção de context."""
        custom_prompt = "Você é um assistente teste. Contexto: {context}"
        prompt_template = get_rag_prompt_template(system_prompt=custom_prompt)

        formatted = prompt_template.format_messages(
            context="Documento de teste",
            question="Dúvida teste?",
        )

        assert "Você é um assistente teste. Contexto: Documento de teste" in formatted[0].content

    def test_get_chat_prompt_template_alias(self) -> None:
        """Valida compatibilidade do alias get_chat_prompt_template."""
        assert get_chat_prompt_template is get_rag_prompt_template
