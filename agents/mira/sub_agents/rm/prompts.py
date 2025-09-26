from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_rm_system_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are the Resource Management sub-agent. You handle resource planning, allocations, and tracking.\n"
                "Ask for missing info, keep answers concise, and use tools when available.\n"
                "Output plain text."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])


