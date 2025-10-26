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
        
        print(f"🗓️ Calendar check result: {result}")

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
    
    CRITICAL: start_date and end_date MUST be in YYYY-MM-DD format (e.g., '2025-10-27').
    DO NOT pass relative dates like 'tomorrow' or 'Monday' - always convert to YYYY-MM-DD first.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (e.g., '2025-10-27'), NOT relative
        end_date: End date in YYYY-MM-DD format (e.g., '2025-10-27'), NOT relative
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
        import re
        from datetime import datetime
        
        print(f"🔍 query_user_calendar called with start_date='{start_date}', end_date='{end_date}', user_email='{user_email}'")
        
        # Validate date format - must be YYYY-MM-DD
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
            error_msg = f"Dates must be in YYYY-MM-DD format. Received: start_date='{start_date}', end_date='{end_date}'"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": "Invalid date format",
                "message": error_msg
            }
        
        # Check if date is in the past (likely a mistake)
        try:
            date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            today = datetime.now()
            if date_obj < today and (today - date_obj).days > 30:
                print(f"⚠️ Warning: Querying date from the past: {start_date}")
        except:
            pass
        
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
    """Send a Google Chat card to supervisor asking approval for the leave request.
    
    Args:
        request_id: Unique leave request identifier
        supervisor_email: Supervisor's email address
        summary: Summary of the request (legacy parameter)
    
    Returns:
        Dict with status, request_id, and supervisor_email
    """
    try:
        print(f"\n{'='*70}")
        print(f"📤 STEP 1: Starting supervisor approval workflow")
        print(f"   Request ID: {request_id}")
        print(f"   Supervisor Email: {supervisor_email}")
        print(f"{'='*70}\n")
        
        # Import utilities
        from agents.utils import db_util, user_context
        import httpx
        
        # Get leave request details from database
        print(f"📋 STEP 2: Retrieving leave request from database...")
        leave_request = db_util.get_leave_request(request_id)
        
        if not leave_request:
            print(f"❌ Leave request {request_id} not found in database")
            return {"status": "ERROR", "request_id": request_id, "error": "Request not found"}
        
        print(f"✅ Retrieved leave request:")
        print(f"   Employee: {leave_request.get('employee_email')}")
        print(f"   Leave Type: {leave_request.get('leave_type')}")
        print(f"   Dates: {leave_request.get('start_date')} to {leave_request.get('end_date')}")
        print(f"   Current Status: {leave_request.get('status')}")
        
        # Get supervisor info including chat_id
        print(f"\n🔍 STEP 3: Looking up supervisor information...")
        print(f"   Searching for: {supervisor_email}")
        supervisor_info = user_context.get_supervisor_info(supervisor_email)
        
        if not supervisor_info:
            print(f"❌ Supervisor {supervisor_email} not found in database")
            return {"status": "ERROR", "request_id": request_id, "error": "Supervisor not found"}
        
        supervisor_space = supervisor_info.get("chat_id")
        supervisor_name = supervisor_info.get("supervisor_name", supervisor_email)
        
        print(f"✅ Found supervisor:")
        print(f"   Name: {supervisor_name}")
        print(f"   Email: {supervisor_info.get('supervisor_email')}")
        
        if not supervisor_space:
            print(f"❌ Supervisor {supervisor_email} has no chat_id configured")
            return {"status": "ERROR", "request_id": request_id, "error": "Supervisor chat_id not configured"}
        
        print(f"   Chat ID: {supervisor_space}")
        
        # Get employee name from database
        print(f"\n👤 STEP 4: Retrieving employee information...")
        employee_info = user_context.get_user_context_from_db(leave_request.get("employee_email"))
        employee_name = employee_info.get("emp_name", leave_request.get("employee_email")) if employee_info else leave_request.get("employee_email")
        
        print(f"✅ Employee: {employee_name} ({leave_request.get('employee_email')})")
        
        # Send approval card via API
        print(f"\n📨 STEP 5: Preparing to send approval card...")
        import os
        port = int(os.getenv("PORT", 3005))
        
        print(f"   API Endpoint: http://localhost:{port}/chat/send-approval-card")
        print(f"   Target Space: {supervisor_space}")
        print(f"   Card Details:")
        print(f"      - Employee: {employee_name} ({leave_request.get('employee_email')})")
        print(f"      - Leave Type: {leave_request.get('leave_type')}")
        print(f"      - Dates: {leave_request.get('start_date')} to {leave_request.get('end_date')}")
        print(f"      - Reason: {leave_request.get('reason')}")
        
        async def send_card():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{port}/chat/send-approval-card",
                    json={
                        "requestId": request_id,
                        "employeeEmail": leave_request.get("employee_email"),
                        "employeeName": employee_name,
                        "supervisorEmail": supervisor_email,
                        "supervisorSpace": supervisor_space,
                        "leaveType": leave_request.get("leave_type"),
                        "startDate": leave_request.get("start_date"),
                        "endDate": leave_request.get("end_date"),
                        "reason": leave_request.get("reason")
                    }
                )
                return response.json()
        
        # Run the async function
        print(f"\n🚀 STEP 6: Sending approval card to supervisor...")
        import asyncio
        result = asyncio.run(send_card())
        
        if result.get("success"):
            print(f"✅ SUCCESS: Approval card sent to supervisor!")
            print(f"   Message ID: {result.get('messageId')}")
            print(f"   Space: {result.get('space')}")
            print(f"   Request ID: {request_id}")
            print(f"\n{'='*70}")
            print(f"✅ Leave approval workflow completed successfully")
            print(f"{'='*70}\n")
            return {"status": "SENT", "request_id": request_id, "supervisor_email": supervisor_email}
        else:
            print(f"❌ FAILED: Could not send approval card")
            print(f"   Error: {result}")
            print(f"\n{'='*70}")
            print(f"❌ Leave approval workflow failed")
            print(f"{'='*70}\n")
            return {"status": "ERROR", "request_id": request_id, "error": "Failed to send card"}
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: Error in supervisor approval workflow")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n{'='*70}")
        print(f"❌ Leave approval workflow failed with exception")
        print(f"{'='*70}\n")
        return {"status": "ERROR", "request_id": request_id, "error": str(e)}


@tool
def record_leave_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record or update a leave request in the database. Returns {'request_id': '...', 'status': '...'}.

    Args:
        payload: Dict containing leave request details including:
            - request_id: Optional unique identifier
            - employee_email: Employee email
            - supervisor_email: Supervisor email
            - leave_type: Type of leave
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)
            - reason: Reason for leave
            - employee_space: Employee's Google Chat space ID
            - status: Request status (default: PENDING)
    """
    try:
        from agents.utils import db_util
        
        # Generate request_id if not provided
        request_id = payload.get("request_id") or f"req_{abs(hash(str(payload))) % (10**8)}"
        
        # Create or update leave request in database
        result = db_util.create_leave_request({
            "request_id": request_id,
            "employee_email": payload.get("employee_email"),
            "supervisor_email": payload.get("supervisor_email"),
            "leave_type": payload.get("leave_type"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "reason": payload.get("reason"),
            "employee_space": payload.get("employee_space"),
            "status": payload.get("status", "PENDING")
        })
        
        return {"request_id": request_id, "status": result.get("status", "CREATED")}
        
    except Exception as e:
        print(f"❌ Error recording leave request: {e}")
        # Fallback to generating request_id on error
        request_id = payload.get("request_id") or f"req_{abs(hash(str(payload))) % (10**8)}"
        return {"request_id": request_id, "status": "ERROR", "error": str(e)}


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
        # Include employee_space (from space_name parameter) in the payload
        rec = record_leave_request.invoke({"payload": {**payload, "employee_space": space_name, "status": "PENDING"}})
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


