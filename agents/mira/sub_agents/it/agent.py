from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

from agents.config.llm_config import get_llm
from .prompts import get_it_system_prompt
from .tools import IT_TOOLS
from .rag_tools import IT_RAG_TOOLS


def get_it_agent_executor() -> AgentExecutor:
    llm = get_llm()
    prompt = get_it_system_prompt()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    tools = IT_TOOLS + IT_RAG_TOOLS
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)


