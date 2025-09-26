from typing import Dict, Any
from langchain_core.tools import tool


@tool
def allocate_resource(resource_type: str, quantity: int, project: str) -> Dict[str, Any]:
    """Allocate a resource to a project. Stub tool."""
    return {"status": "ALLOCATED", "resource_type": resource_type, "quantity": quantity, "project": project}


RM_TOOLS = [allocate_resource]


