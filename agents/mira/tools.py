from multiprocessing import util
from langchain_core.tools import tool
from langchain.tools.base import StructuredTool
from typing import Dict

from .sub_agents.hr.agent import get_hr_agent_executor
from .sub_agents.it.agent import get_it_agent_executor
from .sub_agents.rm.agent import get_rm_agent_executor
from .sub_agents.sql.agent import get_sql_agent_executor
from .sub_agents.finance.agent import get_finance_agent_executor
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

# Special wrapper for HR agent that can accept user context
def _make_hr_agent_tool(name: str, description: str, executor_factory):
    def _run(task: str, user_context: str = "") -> str:
        from datetime import datetime
        today_iso = datetime.now().date().isoformat()
        
        executor = executor_factory()
        # Include user context and today's date in the input if provided
        date_context = f"Today's date: {today_iso}. When I mention relative dates, interpret them relative to today's date.\n\n"
        full_input = f"{user_context}\n\n{date_context}{task}" if user_context else f"{date_context}{task}"
        result = executor.invoke({"input": full_input})
        return result.get("output", "")

    return StructuredTool.from_function(
        func=_run,
        name=name,
        description=description,
    )

# Special wrapper for IT agent that can accept user context
def _make_it_agent_tool(name: str, description: str, executor_factory):
    def _run(task: str, user_context: str = "") -> str:
        executor = executor_factory()
        # Include user context in the input if provided
        full_input = f"{user_context}\n\n{task}" if user_context else task
        result = executor.invoke({"input": full_input})
        return result.get("output", "")

    return StructuredTool.from_function(
        func=_run,
        name=name,
        description=description,
    )


HR_Agent = _make_hr_agent_tool(
    name="HR_Agent",
    description="Answer HR-related tasks and perform HR workflows (leave, policy, etc.). Input is the user's request. Can accept user_context parameter.",
    executor_factory=get_hr_agent_executor,
)

IT_Agent = _make_it_agent_tool(
    name="IT_Agent",
    description="Handle IT support tasks and troubleshooting. Input is the user's request. Can accept user_context parameter.",
    executor_factory=get_it_agent_executor,
)

RM_Agent = _make_agent_tool(
    name="RM_Agent",
    description="Do resource management tasks. Input is the user's request.",
    executor_factory=get_rm_agent_executor,
)

SQL_Agent = _make_agent_tool(
    name="SQL_Agent",
    description="Answer database-related questions by generating and executing read-only SQL (SELECT/WITH/EXPLAIN) on PostgreSQL. Input is the user's request.",
    executor_factory=get_sql_agent_executor,
)

Finance_Agent = _make_agent_tool(
    name="Finance_Agent",
    description="Handle finance questions (pegging rates, revenue, invoices). Input is the user's request.",
    executor_factory=get_finance_agent_executor,
)

# Combine sub-agent tools with RAG tools
TOOLS = [HR_Agent, IT_Agent, RM_Agent, Finance_Agent, SQL_Agent] + RAG_TOOLS
