from langchain_core.tools import tool
from ..sql.agent import get_sql_agent_executor


def _sanitize_user_text(text: str) -> str:
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


@tool("run_finance_sql")
def run_finance_sql(natural_language_request: str) -> str:
    """
    Invoke the SQL sub-agent with a natural-language finance request (pegging, revenue, invoices).
    Returns a sanitized, user-friendly text response.
    """
    try:
        executor = get_sql_agent_executor()
        result = executor.invoke({"input": natural_language_request})
        return _sanitize_user_text(result.get("output", ""))
    except Exception:
        return "I couldn’t retrieve that information right now. Please try again in a moment."


FINANCE_TOOLS = [run_finance_sql]
