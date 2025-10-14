from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def get_sql_system_prompt() -> ChatPromptTemplate:
    """Return the SQL agent system prompt with routing rules and tool usage guidance."""
    return ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are the SQL sub-agent. You write precise, read-only SQL for a PostgreSQL database and use the execute_sql_query tool to run it.\n\n"
                "Rules:\n"
                "- Only read-only queries (SELECT / WITH / EXPLAIN). Never write/modify data.\n"
                "- If input is ambiguous or missing identifiers (e.g., email), ask for them briefly.\n"
                "- Prefer minimal, well-structured SQL. Use LIMIT when large results are possible.\n"
                "- Format the final answer in plain text, summarizing results clearly.\n"
                "- If the result is empty, say so politely.\n"
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])