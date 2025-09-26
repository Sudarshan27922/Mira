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
from .tools import HR_Agent, IT_Agent, RM_Agent

tools = [HR_Agent, IT_Agent, RM_Agent]

# In-memory conversational buffer
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Mira, a friendly and helpful workplace assistant. You have access to company policies and can help with various workplace questions. You can also delegate tasks and use specialized tools provided by your sub-agents to assist users with a wide range of requests.\n\nBe professional, supportive, and concise. Offer actionable help and short examples when useful.\n\nAlways maintain a warm, helpful tone while being professional and accurate. Respond in plain text only (no markdown, no bullets)."),
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


def main_agent(user_prompt: str) -> str:
    
    today_iso = datetime.now(timezone.utc).date().isoformat()
    
    # Add date context to the user prompt
    full_prompt = f"Today's date: {today_iso}. When I mention relative dates (e.g., 'next Monday'), interpret them relative to today's date.\n\n{user_prompt}"

    # Get the response from the agent executor
    response = main_agent_executor.invoke({"input": full_prompt})

    # Print the response
    
    return response["output"]

