from typing import Dict, Any
from langchain_core.tools import tool
import os


@tool
def check_calendar_conflicts(user_email: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Check Google Calendar for conflicts within the given date range for the user.
    
    Args:
        user_email: User's email address
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dict with conflicts list and metadata
    """
    try:
        # Import here to avoid circular dependencies
        from agents.utils.calendar_utils import get_user_calendar_events, format_conflicts_message
        
        # Get configuration from environment
        use_domain_delegation = os.getenv("USE_DOMAIN_DELEGATION", "true").lower() == "true"
        
        # Check calendar for events
        result = get_user_calendar_events(user_email, start_date, end_date, use_domain_delegation)
        
        if result.get("status") == "error":
            print(f"⚠️ Calendar check failed: {result.get('error')}")
            # Return no conflicts on error to not block the workflow
            return {
                "conflicts": [],
                "error": result.get("error"),
                "status": "error"
            }
        
        conflicts = result.get("conflicts", [])
        
        if conflicts:
            conflicts_message = format_conflicts_message(conflicts)
            return {
                "conflicts": conflicts,
                "total": len(conflicts),
                "message": conflicts_message,
                "status": "conflicts_found"
            }
        
        return {
            "conflicts": [],
            "message": "No calendar conflicts found for the requested dates.",
            "status": "no_conflicts"
        }
        
    except Exception as e:
        print(f"❌ Error in check_calendar_conflicts: {str(e)}")
        # Return no conflicts on error to not block the workflow
        return {
            "conflicts": [],
            "error": str(e),
            "status": "error"
        }


@tool
def query_user_calendar(start_date: str, end_date: str, user_email: str = "") -> Dict[str, Any]:
    """Query a user's Google Calendar for events within the given date range.
    
    This tool retrieves calendar events and returns formatted information about meetings/events.
    Use this to:
    - Check if user has meetings during a time period
    - View user's schedule for coordination
    - Identify potential conflicts before scheduling
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        user_email: User's email (required - use user_context['emp_email'])
        
    Returns:
        Dict with formatted calendar information:
        - events: List of calendar events with details
        - total_events: Count of events found
        - message: Human-readable summary
        - date_range: The queried date range
    """
    try:
        from agents.utils.calendar_utils import get_user_calendar_events
        
        # If no user_email provided, this will fail - HR agent should always provide it
        if not user_email:
            return {
                "status": "error",
                "error": "user_email is required",
                "message": "Please provide the user's email address to query their calendar."
            }
        
        # Get configuration from environment
        use_domain_delegation = os.getenv("USE_DOMAIN_DELEGATION", "true").lower() == "true"
        
        # Query calendar
        result = get_user_calendar_events(user_email, start_date, end_date, use_domain_delegation)
        
        if result.get("status") == "error":
            return {
                "status": "error",
                "error": result.get("error"),
                "message": f"Unable to retrieve calendar for {user_email}. They may need to share their calendar."
            }
        
        events = result.get("conflicts", [])  # "conflicts" is a misnomer, these are just events
        
        if not events:
            return {
                "status": "success",
                "events": [],
                "total_events": 0,
                "message": f"No events found for {user_email} from {start_date} to {end_date}.",
                "date_range": {"start": start_date, "end": end_date}
            }
        
        # Format events into readable message
        message = f"📅 Found {len(events)} event(s) for {user_email} from {start_date} to {end_date}:\n\n"
        
        for i, event in enumerate(events, 1):
            from datetime import datetime
            start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            summary = event.get('summary', 'Untitled Event')
            location = event.get('location', '')
            
            message += f"{i}. {summary}\n"
            message += f"   📅 {start_dt.strftime('%B %d, %Y at %I:%M %p')}\n"
            if location:
                message += f"   📍 {location}\n"
            if event.get('attendees', 0) > 0:
                message += f"   👥 {event['attendees']} attendee(s)\n"
            message += "\n"
        
        return {
            "status": "success",
            "events": events,
            "total_events": len(events),
            "message": message,
            "date_range": {"start": start_date, "end": end_date}
        }
        
    except Exception as e:
        print(f"❌ Error in query_user_calendar: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to query calendar. Please try again."
        }


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
            conflicts_message = conflicts.get("message", "Conflicts found. Proceed anyway or choose new dates?")
            return {
                "status": "WAITING_USER_DECISION",
                "request_id": request_id,
                "conflicts": conflicts["conflicts"],
                "total_conflicts": conflicts.get("total", len(conflicts.get("conflicts", []))),
                "message": conflicts_message
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
    query_user_calendar,
]


