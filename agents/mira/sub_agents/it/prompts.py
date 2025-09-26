from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_it_system_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are the IT sub-agent. You troubleshoot devices, accounts, network, and software.\n"
                "Ask clarifying questions only when needed. Prefer using tools when available.\n"
                "Output plain text."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])


