from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from agents.config.llm_config import get_llm
from .prompts import get_sql_system_prompt
from .tools import execute_sql_query

def get_sql_agent_executor() -> AgentExecutor:
    llm = get_llm()
    prompt = get_sql_system_prompt()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent = create_tool_calling_agent(llm, [execute_sql_query], prompt)
    return AgentExecutor(
        agent=agent,
        tools=[execute_sql_query],
        memory=memory,
        verbose=True,
        max_iterations=5,
        early_stopping_method="generate",
    )