from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
try:
    from langchain.tools import StructuredTool
except Exception:
    from langchain_core.tools import StructuredTool
from langchain_core.tools import tool

from .jira_service import JiraService
from agents.config.jira_config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY

# Single Jira client
svc = JiraService(JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY)

def _create_jira_ticket(
    summary: str,
    description: Optional[str] = None,
    issue_type: str = "Service Request",
    priority: Optional[str] = None,
    labels: Optional[List[str]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> str:
    desc = description or summary
    return svc.create_ticket(
        summary=summary,
        description=desc,
        issue_type=issue_type,
        priority=priority,
        labels=labels,
        custom_fields=custom_fields,
    )

class CreateJiraTicketInput(BaseModel):
    summary: str = Field(..., description="One-line summary.")
    description: Optional[str] = Field(None, description="Full description.")
    issue_type: str = Field("Service Request", description="Issue type name (will be resolved).")
    priority: Optional[str] = Field(None, description="Low, Medium, High, Critical.")
    labels: Optional[List[str]] = Field(None, description="Labels.")
    custom_fields: Optional[Dict[str, Any]] = Field(
        None, description="Logical custom fields: product, requested_for, location, approver, due_date (yyyy-MM-dd or natural language), intent."
    )

create_jira_ticket = StructuredTool.from_function(
    name="create_jira_ticket",
    description="Create a Jira ticket for any IT request (hardware, software, account, network, incidents).",
    func=_create_jira_ticket,
    args_schema=CreateJiraTicketInput,
)

@tool
def get_it_request_status(issue_key: str) -> Dict[str, Any]:
    """Get the workflow status of a Jira issue by key (e.g., ITSD-123)."""
    return svc.get_request_status(issue_key)

IT_TOOLS = [create_jira_ticket, get_it_request_status]
__all__ = ["create_jira_ticket", "get_it_request_status", "IT_TOOLS"]


