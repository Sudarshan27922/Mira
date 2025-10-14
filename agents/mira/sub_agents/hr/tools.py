from typing import Dict, Any
from langchain_core.tools import tool
import httpx
import os


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
def leave_process_workflow(payload: Dict[str, Any], space_name: str = None) -> Dict[str, Any]:
    """Composite workflow: validate -> check conflicts -> (maybe) request decision -> approval -> finalize.

    This is a stubbed synchronous version; later replace with LangGraph and persistence.
    Returns a dict with at least {'status': str, 'request_id': str}.
    """
    # Check if this is a card response with complete data
    if all(payload.get(k) for k in ["employee_email", "leave_type", "start_date", "end_date", "reason", "supervisor_email"]):
        # Complete data provided - proceed with normal workflow
        rec = record_leave_request.invoke({"payload": {**payload, "status": "COLLECTED"}})
        request_id = rec["request_id"]

        conflicts = check_calendar_conflicts.invoke({
            "user_email": payload["employee_email"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
        })
        if conflicts.get("conflicts"):
            return {
                "status": "WAITING_USER_DECISION",
                "request_id": request_id,
                "conflicts": conflicts["conflicts"],
                "message": "Conflicts found. Proceed anyway or choose new dates?"
            }

        send_supervisor_approval.invoke({
            "request_id": request_id,
            "supervisor_email": payload["supervisor_email"],
            "summary": "Leave approval request",
        })
        return {"status": "WAITING_SUPERVISOR", "request_id": request_id}
    
    # Incomplete data - check if we have minimum required info to send card
    elif payload.get("employee_email") and payload.get("supervisor_email") and space_name:
        # Generate request ID and send card
        import time
        request_id = f"req_{int(time.time())}_{hash(payload['employee_email']) % 10000}"
        
        # Send the interactive card
        card_result = send_leave_info_card.invoke({
            "user_email": payload["employee_email"],
            "space_name": space_name,
            "supervisor_email": payload["supervisor_email"],
            "request_id": request_id
        })
        
        if card_result.get("status") == "CARD_SENT":
            return {
                "status": "WAITING_CARD_RESPONSE",
                "request_id": request_id,
                "message": "Interactive leave request form sent. Please fill in the details and submit."
            }
        else:
            return {
                "status": "ERROR",
                "request_id": request_id,
                "error": card_result.get("error", "Failed to send leave request card")
            }
    
    # Missing required fields
    else:
        required = ["employee_email", "supervisor_email"]
        missing = [k for k in required if not payload.get(k)]
        if missing:
            return {"status": "MISSING_FIELDS", "missing": missing}
        
        return {"status": "MISSING_SPACE", "message": "Space name required to send leave request card"}


@tool
def send_leave_info_card(user_email: str, space_name: str, supervisor_email: str, request_id: str) -> Dict[str, Any]:
    """Send an interactive leave request card to the user for collecting leave details.
    
    Args:
        user_email: Employee email address
        space_name: Google Chat space name
        supervisor_email: Supervisor's email address
        request_id: Unique request identifier
        
    Returns:
        Dict with status and request details
    """
    try:
        port = int(os.getenv("PORT", 3005))
        
        # Call the server endpoint to send the leave card
        with httpx.Client() as client:
            response = client.post(
                f"http://localhost:{port}/chat/send-leave-card",
                json={
                    "spaceName": space_name,
                    "employeeEmail": user_email,
                    "supervisorEmail": supervisor_email,
                    "requestId": request_id
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "CARD_SENT",
                    "request_id": request_id,
                    "space_name": space_name,
                    "employee_email": user_email,
                    "supervisor_email": supervisor_email,
                    "message": "Leave request card sent successfully"
                }
            else:
                return {
                    "status": "ERROR",
                    "request_id": request_id,
                    "error": f"Failed to send card: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        return {
            "status": "ERROR",
            "request_id": request_id,
            "error": f"Exception while sending card: {str(e)}"
        }


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
    send_leave_info_card,
]


