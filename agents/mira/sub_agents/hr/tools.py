from typing import Dict, Any
from langchain_core.tools import tool


@tool
def check_calendar_conflicts(user_email: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Check Google Calendar for conflicts within the given date range for the user. Returns {'conflicts': [...]}.

    This is a stub; implement Google Calendar API lookup later.
    """
    return {"conflicts": []}


@tool
def send_supervisor_approval(request_id: str, supervisor_email: str, summary: str) -> Dict[str, Any]:
    """Send a Google Chat card to supervisor asking approval for the given request_id. Returns status placeholder.

    This is a stub; implement Google Chat card send and callback correlation later.
    """
    return {"status": "SENT", "request_id": request_id, "supervisor_email": supervisor_email}


@tool
def record_leave_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record or update a leave request in persistence. Returns {'request_id': '...'}.

    This is a stub; wire to DB later. Generates a deterministic-ish placeholder id when missing.
    """
    request_id = payload.get("request_id") or f"req_{abs(hash(str(payload))) % (10**8)}"
    return {"request_id": request_id, "status": payload.get("status", "CREATED")}


@tool
def leave_process_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Composite workflow: validate -> check conflicts -> (maybe) request decision -> approval -> finalize.

    This is a stubbed synchronous version; later replace with LangGraph and persistence.
    Returns a dict with at least {'status': str, 'request_id': str}.
    """
    required = ["employee_email", "leave_type", "start_date", "end_date", "reason", "supervisor_email"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return {"status": "MISSING_FIELDS", "missing": missing}

    rec = record_leave_request.run(payload={**payload, "status": "COLLECTED"})
    request_id = rec["request_id"]

    conflicts = check_calendar_conflicts.run(payload["employee_email"], payload["start_date"], payload["end_date"])  # type: ignore[arg-type]
    if conflicts.get("conflicts"):
        return {
            "status": "WAITING_USER_DECISION",
            "request_id": request_id,
            "conflicts": conflicts["conflicts"],
            "message": "Conflicts found. Proceed anyway or choose new dates?"
        }

    send_supervisor_approval.run(request_id, payload["supervisor_email"], "Leave approval request")  # type: ignore[arg-type]
    return {"status": "WAITING_SUPERVISOR", "request_id": request_id}


@tool
def leave_process_resume(request_id: str, decision: str = "proceed", new_start_date: str | None = None, new_end_date: str | None = None) -> Dict[str, Any]:
    """Resume a paused leave process. If decision=='proceed', continue; if 'change_dates', re-check conflicts.

    Stub implementation; integrate with workflow engine later.
    """
    if decision == "change_dates":
        if not (new_start_date and new_end_date):
            return {"status": "MISSING_FIELDS", "missing": ["new_start_date", "new_end_date"], "request_id": request_id}
        # Assume conflicts resolved after change in stub
        return {"status": "DATES_UPDATED", "request_id": request_id, "start_date": new_start_date, "end_date": new_end_date}
    # proceed
    return {"status": "REQUESTING_APPROVAL", "request_id": request_id}


HR_TOOLS = [
    check_calendar_conflicts,
    send_supervisor_approval,
    record_leave_request,
    leave_process_workflow,
    leave_process_resume,
]


