from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

from agents.config.llm_config import get_llm
from .prompts import get_finance_system_prompt
from .tools import FINANCE_TOOLS


def get_finance_agent_executor() -> AgentExecutor:
    llm = get_llm()
    prompt = get_finance_system_prompt()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent = create_tool_calling_agent(llm, FINANCE_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=FINANCE_TOOLS, memory=memory, verbose=True)
