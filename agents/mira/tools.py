from langchain_core.tools import tool
from langchain.tools.base import StructuredTool
from typing import Dict

from .sub_agents.hr.agent import get_hr_agent_executor
from .sub_agents.it.agent import get_it_agent_executor
from .sub_agents.rm.agent import get_rm_agent_executor
from .rag_tool import RAG_TOOLS


# Wrap sub-agent executors as tools callable by the main agent
def _make_agent_tool(name: str, description: str, executor_factory):
    def _run(task: str) -> str:
        executor = executor_factory()
        result = executor.invoke({"input": task})
        return result.get("output", "")

    return StructuredTool.from_function(
        func=_run,
        name=name,
        description=description,
    )


HR_Agent = _make_agent_tool(
    name="HR_Agent",
    description="Answer HR-related tasks and perform HR workflows (leave, policy, etc.). Input is the user's request.",
    executor_factory=get_hr_agent_executor,
)

IT_Agent = _make_agent_tool(
    name="IT_Agent",
    description="Handle IT support tasks and troubleshooting. Input is the user's request.",
    executor_factory=get_it_agent_executor,
)

RM_Agent = _make_agent_tool(
    name="RM_Agent",
    description="Do resource management tasks. Input is the user's request.",
    executor_factory=get_rm_agent_executor,
)

# Combine sub-agent tools with RAG tools
TOOLS = [HR_Agent, IT_Agent, RM_Agent] + RAG_TOOLS
