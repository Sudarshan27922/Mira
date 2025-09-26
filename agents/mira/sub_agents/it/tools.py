from typing import Dict, Any
from langchain_core.tools import tool


@tool
def diagnose_connectivity(issue_description: str) -> Dict[str, Any]:
    """Suggest initial steps for network connectivity issues. Stub tool."""
    return {"steps": ["Check Wi-Fi connection", "Restart router", "Run ping test"]}


IT_TOOLS = [diagnose_connectivity]


