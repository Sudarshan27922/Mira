from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_rm_system_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are the Resource Management (RM) sub-agent. You handle projects, allocations, staffing, and resource planning.\n"
                "Behaviors:\n"
                "- If the user's request is general (e.g., 'project info'), ask concise clarifying questions: project name and what info is needed (status, start/end dates, manager, team members, allocation %, open roles, etc.).\n"
                "- Once you have enough details, call the run_sql_agent tool with a clear natural-language request describing what to fetch.\n"
                "- Do NOT assume a table doesn't exist without checking. Ask the SQL agent to list_public_tables and describe_table_columns as needed.\n"
                "- Keep answers short, precise, and in plain text."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])


