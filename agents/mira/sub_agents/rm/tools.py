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


@tool("get_allocation_info")
def get_allocation_info(request: str) -> str:
    """Retrieve allocation info by delegating to the SQL agent with an allocation-focused request.

    Use this when the user asks about allocation percentage, type, role, dates, whether allocated, end_notified, resource details,
    segment, or on-site/off-site location. Automatically asks the SQL agent to look into the allocation table
    and join employee for resource name/email.
    """
    try:
        executor = get_sql_agent_executor()
        nl = (
            "You are checking allocation data. Verify allocation table columns using describe_table_columns if needed. "
            "Answer only from the allocation table and join to employee on allocation.resource_id = employee.id for names/emails. "
            "Respect time filters if provided (current = today between start_date and end_date; or overlap with a range). "
            "Return a concise, non-technical summary. Query to fulfill: " + request
        )
        result = executor.invoke({"input": nl})
        return _sanitize_user_text(result.get("output", ""))
    except Exception:
        return "I couldn’t retrieve the allocation details right now. Please try again shortly."


RM_TOOLS = [allocate_resource, run_sql_agent, get_allocation_info]


