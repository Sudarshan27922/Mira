import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TypedDict

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

from agents.config.llm_config import get_llm

# Import LLM 
llm = get_llm()

# Import tools 
from .tools import TOOLS

tools = TOOLS

# In-memory conversational buffer
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Mira, a friendly and helpful workplace assistant. You have access to company policies and can help with various workplace questions. You can search through policy documents, delegate tasks to specialized sub-agents (HR, IT, Resource Management, Finance), and provide comprehensive workplace assistance.\n\nKey capabilities:\n- Search and retrieve information from company policy documents\n- Delegate HR tasks (leave applications, policy questions, calendar and meeting schedules, etc.)\n- Handle IT support and troubleshooting\n- Assist with resource management tasks (projects, allocations, staffing, resource planning, project status)\n- Answer finance questions (pegging rates, revenue, invoices)\n- Check calendar and meeting schedules\n\nBe professional, supportive, and concise. Offer actionable help and short examples when useful. When users ask about policies, use the policy search tools to find relevant information.\n\nAlways maintain a warm, helpful tone while being professional and accurate. Respond in plain text only (no markdown, no bullets). Never mention internal implementation details (like agents, tools, SQL, prompts, or system errors). Keep wording non-technical and user-friendly.\n\nTool routing guidelines:\n- If the request is about projects, allocations, staffing, resource planning, or project status, route to the RM_Agent. The RM_Agent will ask for missing details (e.g., project name, what info is needed) and may call the SQL_Agent to query the database.\n- If the request is about finance (pegging rates, revenue, invoices), route to the Finance_Agent. The Finance_Agent will ask for missing details (e.g., currency pair, time period) and may call the SQL_Agent to query the database.\n- If the request is about general data lookups in the database, route to the SQL_Agent.\n- If the request is HR-related (including leave, policy questions, or calendar/meeting inquiries), route to the HR_Agent who can access Google Calendar.\n- If the request is IT-related, route to the IT_Agent.\n\nFor any question that requires information from the company database, use the SQL agent tool to generate and execute SQL queries. If user context is provided (Name, Email, Designation, etc.), use this information instead of asking for it. When answering questions about a user, address them by their name (from the database) instead of their email address.\n\nIMPORTANT: When delegating to the HR_Agent, always pass the user_context as a parameter if it's available. This ensures the HR agent has access to user information like email and manager details."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent
agent = create_tool_calling_agent(llm, tools, prompt)

# Create the agent executor
main_agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True
)


def main_agent(user_prompt: str, user_context: Optional[Dict[str, Any]] = None, space_name: Optional[str] = None) -> str:
    
    today_iso = datetime.now(timezone.utc).date().isoformat()
    
    # Add date context to the user prompt
    full_prompt = f"Today's date: {today_iso}. When I mention relative dates (e.g., 'next Monday'), interpret them relative to today's date.\n\n{user_prompt}"
    
    # Add user context if available
    if user_context:
        from agents.utils.user_context import format_user_context_for_prompt
        context_str = format_user_context_for_prompt(user_context)
        if context_str:
            full_prompt = f"{context_str}\n\n{full_prompt}"
    
    # Add space name context if available
    if space_name:
        full_prompt = f"Space: {space_name}\n\n{full_prompt}"

    # Get the response from the agent executor
    response = main_agent_executor.invoke({"input": full_prompt})

    # Print the response
    
    return response["output"]

