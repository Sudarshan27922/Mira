from typing import Dict, Any
from langchain_core.tools import tool

from ..sql.agent import get_sql_agent_executor


@tool
def allocate_resource(resource_type: str, quantity: int, project: str) -> Dict[str, Any]:
    """Allocate a resource to a project. Stub tool."""
    return {"status": "ALLOCATED", "resource_type": resource_type, "quantity": quantity, "project": project}


def _sanitize_user_text(text: str) -> str:
    """Remove technical/internal references from text for end-user display."""
    if not isinstance(text, str):
        return text
    replacements = {
        "SQL agent": "data service",
        "SQL Agent": "data service",
        "tool": "process",
        "tools": "processes",
        "query": "check",
        "Query": "Check",
        "schema": "data",
        "database schema": "data",
        "execute": "run",
        "execution": "processing",
    }
    out = text
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


@tool("run_sql_agent")
def run_sql_agent(natural_language_request: str) -> str:
    """
    Call the SQL sub-agent with a natural language request to inspect schema and query data.
    The SQL agent will use list_public_tables/describe_table_columns/execute_sql_query tools as needed.
    """
    try:
        executor = get_sql_agent_executor()
        result = executor.invoke({"input": natural_language_request})
        return _sanitize_user_text(result.get("output", ""))
    except Exception as e:
        # Return a non-technical message
        return "I couldn’t retrieve that information right now. Please try again in a moment."


RM_TOOLS = [allocate_resource, run_sql_agent]


