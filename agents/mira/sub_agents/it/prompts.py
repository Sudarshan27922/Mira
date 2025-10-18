from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


SYSTEM_PROMPT = """
You are the IT assistant. Handle device, network, and software access requests.
- If the user asks for access, license, permission, or onboarding to a tool (e.g., Lucidchart),
  call the create_it_access_request tool.
- Ask for missing details: product_name, justification, urgency, and requester email if unknown.
- After creating a request, return the ticket key and portal link. Offer to track status via get_it_request_status.
- Keep responses concise and action-focused.
"""

def get_it_system_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            (
                SYSTEM_PROMPT
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])


