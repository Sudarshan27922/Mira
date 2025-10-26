from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
import os


def get_calendar_service():
    """Get or create the calendar service instance"""
    import server.main as main_module
    # Check if calendar_service exists and is not None
    if hasattr(main_module, 'calendar_service') and main_module.calendar_service is not None:
        return main_module.calendar_service
    
    # If not initialized, try to initialize it now
    print("⚠️ Calendar service not initialized, attempting to initialize now...")
    try:
        if hasattr(main_module, 'initialize_google_services'):
            main_module.initialize_google_services()
            return main_module.calendar_service
    except Exception as e:
        print(f"❌ Failed to initialize calendar service: {e}")
    
    return None


def get_user_calendar_events(
    user_email: str,
    start_date: str,
    end_date: str,
    use_domain_delegation: bool = True
) -> Dict[str, Any]:
    """
    Check Google Calendar for events within the date range.
    
    Args:
        user_email: User's email address
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        use_domain_delegation: If True, impersonate the user (requires domain-wide delegation)
        
    Returns:
        Dict with conflicts list and metadata
    """
    try:
        print(f"🔍 Checking calendar for user: {user_email}, dates: {start_date} to {end_date}")
        calendar_service = get_calendar_service()
        
        if not calendar_service:
            print("❌ Calendar service is None or not found")
            return {
                "status": "error",
                "error": "Calendar service not initialized. Please restart the server.",
                "conflicts": []
            }
        
        print(f"✅ Calendar service retrieved successfully")
        
        # Convert dates to RFC3339 format
        start_datetime = f"{start_date}T00:00:00Z"
        end_datetime = f"{end_date}T23:59:59Z"
        
        # If using domain-wide delegation, create delegated credentials
        if use_domain_delegation:
            from google.oauth2 import service_account
            from server.main import SERVICE_ACCOUNT_FILE, SCOPES
            
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=SCOPES
            )
            delegated_credentials = credentials.with_subject(user_email)
            
            from googleapiclient.discovery import build
            user_calendar_service = build('calendar', 'v3', credentials=delegated_credentials)
        else:
            user_calendar_service = calendar_service
        
        # Query calendar events with freebusy-compatible view
        # Note: With "See only free/busy" permission, we get limited details
        try:
            events_result = user_calendar_service.events().list(
                calendarId='primary',
                timeMin=start_datetime,
                timeMax=end_datetime,
                singleEvents=True,
                orderBy='startTime',
                maxResults=250
            ).execute()
        except Exception as e:
            # If we get a permission error, try with minimal access
            if 'insufficient' in str(e).lower() or 'permission' in str(e).lower():
                print(f"⚠️ Limited calendar access - using freebusy view")
                # Use freebusy query as fallback
                return get_freebusy_events(user_email, start_date, end_date, use_domain_delegation)
            raise
        
        events = events_result.get('items', [])
        print(f"🔍 Found {len(events)} total events in calendar")
        
        # Filter and format conflicts
        conflicts = []
        for event in events:
            # Skip all-day events or declined events
            if event.get('start').get('date'):  # All-day event
                print(f"⏭️ Skipping all-day event: {event.get('summary', 'Untitled')}")
                continue
            
            attendee_response = None
            if 'attendees' in event:
                for attendee in event['attendees']:
                    if attendee.get('email') == user_email:
                        attendee_response = attendee.get('responseStatus')
                        break
            
            # Skip if user declined
            if attendee_response == 'declined':
                print(f"⏭️ Skipping declined event: {event.get('summary', 'Untitled')}")
                continue
            
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            print(f"✅ Including event: {event.get('summary', 'Untitled')} at {start}")
            
            conflicts.append({
                "summary": event.get('summary', 'Untitled Event'),
                "start": start,
                "end": end,
                "location": event.get('location', ''),
                "attendees": len(event.get('attendees', [])),
                "status": event.get('status', 'confirmed'),
                "event_id": event.get('id')
            })
        
        return {
            "status": "success",
            "conflicts": conflicts,
            "total_conflicts": len(conflicts),
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }
        
    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else str(error)
        return {
            "status": "error",
            "error": f"Calendar API error: {error_details}",
            "conflicts": []
        }
    except Exception as error:
        return {
            "status": "error",
            "error": f"Failed to check calendar: {str(error)}",
            "conflicts": []
        }


def get_freebusy_events(user_email: str, start_date: str, end_date: str, use_domain_delegation: bool = True) -> Dict[str, Any]:
    """Fallback method using freebusy query when full calendar access is not available.
    
    This is used when calendar is shared with "See only free/busy" permission.
    """
    try:
        print(f"🔄 Using freebusy query for {user_email}")
        
        from google.oauth2 import service_account
        from server.main import SERVICE_ACCOUNT_FILE, SCOPES
        
        if use_domain_delegation:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=SCOPES
            )
            delegated_credentials = credentials.with_subject(user_email)
            from googleapiclient.discovery import build
            user_calendar_service = build('calendar', 'v3', credentials=delegated_credentials)
        else:
            user_calendar_service = get_calendar_service()
            if not user_calendar_service:
                return {"status": "error", "error": "Calendar service not available", "conflicts": []}
        
        # Freebusy query
        start_datetime = f"{start_date}T00:00:00Z"
        end_datetime = f"{end_date}T23:59:59Z"
        
        freebusy_result = user_calendar_service.freebusy().query(body={
            "timeMin": start_datetime,
            "timeMax": end_datetime,
            "items": [{"id": 'primary'}]
        }).execute()
        
        busy_periods = freebusy_result.get('calendars', {}).get('primary', {}).get('busy', [])
        
        if not busy_periods:
            return {
                "status": "success",
                "conflicts": [],
                "total_conflicts": 0,
                "date_range": {"start": start_date, "end": end_date},
                "message": "No busy periods found"
            }
        
        # Format busy periods
        conflicts = []
        for period in busy_periods:
            conflicts.append({
                "summary": "Busy (freebusy)",
                "start": period['start'],
                "end": period['end'],
                "location": "Limited access - details not available",
                "attendees": 0,
                "status": "busy"
            })
        
        print(f"🔄 Found {len(conflicts)} busy period(s)")
        
        return {
            "status": "success",
            "conflicts": conflicts,
            "total_conflicts": len(conflicts),
            "date_range": {"start": start_date, "end": end_date}
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Freebusy query failed: {str(e)}",
            "conflicts": []
        }


def format_conflicts_message(conflicts: List[Dict[str, Any]]) -> str:
    """Format conflicts into a user-friendly message"""
    if not conflicts:
        return "No calendar conflicts found."
    
    # Check if using limited freebusy access
    is_limited_access = conflicts and conflicts[0].get('summary') == 'Busy (freebusy)'
    
    if is_limited_access:
        message = f"⚠️ Found {len(conflicts)} busy period(s) during your leave dates:\n\n"
        message += "(Limited calendar access - showing busy times without event details)\n\n"
    else:
        message = f"⚠️ Found {len(conflicts)} meeting(s) during your leave dates:\n\n"
    
    for i, conflict in enumerate(conflicts, 1):
        start_dt = datetime.fromisoformat(conflict['start'].replace('Z', '+00:00'))
        summary = conflict.get('summary', 'Untitled Event')
        location = conflict.get('location', '')
        
        message += f"{i}. {summary}\n"
        message += f"   📅 {start_dt.strftime('%B %d, %Y at %I:%M %p')}\n"
        if location and not is_limited_access:
            message += f"   📍 {location}\n"
        message += "\n"
    
    message += "Would you like to proceed with the leave request anyway, or choose different dates?"
    return message

