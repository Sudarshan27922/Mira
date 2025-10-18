from typing import Dict, Any, Optional
from langchain_core.tools import tool
from .jira_service import JiraService

@tool
def diagnose_connectivity(issue_description: str) -> Dict[str, Any]:
    """Suggest initial steps for network connectivity issues. Stub tool."""
    return {"steps": ["Check Wi-Fi connection", "Restart router", "Run ping test"]}

@tool
def create_it_access_request(
    product_name: str,
    justification: Optional[str] = None,
    urgency: Optional[str] = "medium",
    requester_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Jira Service Management customer request for application access (e.g., Lucidchart license).
    - product_name: The software or system (e.g., 'Lucidchart').
    - justification: Why access is needed.
    - urgency: low | medium | high | critical (passed in description).
    - requester_email: Employee email; falls back to JIRA_DEFAULT_REQUESTER_EMAIL if unset.
    Returns issueKey, links, and initial status context.
    """
    svc = JiraService()
    summary = f"Access request: {product_name}"
    desc_lines = [
        f"Product: {product_name}",
        f"Urgency: {urgency or 'medium'}",
        f"Justification: {justification or 'Not provided'}",
    ]
    description = "\n".join(desc_lines)

    result = svc.create_customer_request(
        summary=summary,
        description=description,
        requester_email=requester_email,
    )
    # Fetch status right away for user feedback
    status = {}
    try:
        status = svc.get_request_status(result["issueKey"])
    except Exception:
        status = {}

    return {
        "message": f"Created request for {product_name}.",
        "issueKey": result.get("issueKey"),
        "issueId": result.get("issueId"),
        "status": status.get("status"),
        "links": {"portal": result.get("web"), "api": result.get("self")},
    }

@tool
def get_it_request_status(issue_key: str) -> Dict[str, Any]:
    """
    Get the latest status of a Jira Service Management request by issue key (e.g., ITSM-123).
    """
    svc = JiraService()
    data = svc.get_request_status(issue_key)
    return {
        "issueKey": data.get("issueKey"),
        "status": data.get("status"),
        "summary": data.get("summary"),
        "links": {"portal": data.get("web")},
    }

IT_TOOLS = [diagnose_connectivity, create_it_access_request, get_it_request_status]


