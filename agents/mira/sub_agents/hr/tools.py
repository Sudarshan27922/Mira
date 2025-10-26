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
def leave_process_workflow(payload: Dict[str, Any], space_name: str = "") -> Dict[str, Any]:
    """Process complete leave request workflow: validate -> check conflicts -> approval -> finalize.

    This function should ONLY be called when all required data is complete.
    Returns a dict with at least {'status': str, 'request_id': str}.
    """
    # Validate that all required fields are present
    required_fields = ["employee_email", "leave_type", "start_date", "end_date", "reason", "supervisor_email"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    
    if missing_fields:
        return {
            "status": "INCOMPLETE_DATA",
            "missing": missing_fields,
            "message": f"Missing required fields: {', '.join(missing_fields)}. Please collect all data first."
        }
    
    # All data is complete - proceed with workflow
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
    
    return {
        "status": "WAITING_SUPERVISOR", 
        "request_id": request_id,
        "message": "Leave request submitted successfully. Waiting for supervisor approval."
    }


@tool
def send_leave_info_card(user_email: str, space_name: str, supervisor_email: str, request_id: str) -> Dict[str, Any]:
    """Send an interactive leave request card to the user for collecting leave details.
    
    Args:
        user_email: Employee email address
        space_name: Google Chat space name (format: spaces/ABC123)
        supervisor_email: Supervisor's email address
        request_id: Unique request identifier
        
    Returns:
        Dict with status and request details
    """
    try:
        # Debug logging
        print(f"📧 Sending leave info card:")
        print(f"   Space name: {space_name}")
        print(f"   User email: {user_email}")
        print(f"   Supervisor: {supervisor_email}")
        print(f"   Request ID: {request_id}")
        
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


@tool
def collect_leave_data_from_card(user_message: str, existing_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Parse user's leave request message and extract leave data fields.
    
    Args:
        user_message: The user's message containing leave details
        existing_data: Optional existing data to merge with new data
        
    Returns:
        Dict with status, extracted data, and missing fields if incomplete
    """
    try:
        import re
        
        # Normalize the text - remove extra whitespace
        text = user_message.strip()
        
        # Look for structured format patterns
        patterns = {
            'leave_type': r'(?:leave\s+type|type)[:\s]+([^\n\r]+)',
            'start_date': r'(?:start\s+date|from)[:\s]+([^\n\r]+)',
            'end_date': r'(?:end\s+date|to)[:\s]+([^\n\r]+)',
            'reason': r'(?:reason|purpose)[:\s]+([^\n\r]+)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    extracted[field] = value
        
        # Merge with existing data if provided
        if existing_data:
            extracted = {**existing_data, **extracted}
        
        # Validate that we have all required fields
        required_fields = ['leave_type', 'start_date', 'end_date', 'reason']
        missing_fields = [field for field in required_fields if not extracted.get(field)]
        
        if missing_fields:
            return {
                "status": "incomplete",
                "data": extracted,
                "missing": missing_fields,
                "message": f"Missing fields: {', '.join(missing_fields)}"
            }
        
        # Clean up the values
        extracted['leave_type'] = extracted['leave_type'].strip()
        extracted['start_date'] = extracted['start_date'].strip()
        extracted['end_date'] = extracted['end_date'].strip()
        extracted['reason'] = extracted['reason'].strip()
        
        # Basic validation
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not (re.match(date_pattern, extracted['start_date']) and 
                re.match(date_pattern, extracted['end_date'])):
            return {
                "status": "invalid",
                "data": extracted,
                "error": "Invalid date format. Please use YYYY-MM-DD format.",
                "message": "Please use YYYY-MM-DD format for dates (e.g., 2024-01-15)"
            }
        
        # Validate date logic
        from datetime import datetime
        try:
            start_dt = datetime.strptime(extracted['start_date'], '%Y-%m-%d')
            end_dt = datetime.strptime(extracted['end_date'], '%Y-%m-%d')
            
            if start_dt > end_dt:
                return {
                    "status": "invalid",
                    "data": extracted,
                    "error": "Start date cannot be after end date",
                    "message": "Please check your dates - start date cannot be after end date"
                }
        except ValueError:
            return {
                "status": "invalid",
                "data": extracted,
                "error": "Invalid date format",
                "message": "Please use YYYY-MM-DD format for dates (e.g., 2024-01-15)"
            }
        
        return {
            "status": "complete",
            "data": extracted,
            "message": "All leave data collected successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error parsing leave data: {str(e)}",
            "message": "There was an error processing your leave details. Please try again."
        }


HR_TOOLS = [
    check_calendar_conflicts,
    send_supervisor_approval,
    record_leave_request,
    leave_process_workflow,
    leave_process_resume,
    send_leave_info_card,
    collect_leave_data_from_card,
]


