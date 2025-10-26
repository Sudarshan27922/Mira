from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
import os


def get_calendar_service():
    """Get the calendar service instance from main.py"""
    try:
        # Import here to avoid circular import issues during initialization
        import server.main as main_module
        return main_module.calendar_service
    except (ImportError, AttributeError) as e:
        print(f"⚠️ Calendar service not available: {e}")
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
        calendar_service = get_calendar_service()
        
        if not calendar_service:
            return {
                "status": "error",
                "error": "Calendar service not initialized",
                "conflicts": []
            }
        
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
        
        # Query calendar events
        events_result = user_calendar_service.events().list(
            calendarId='primary',
            timeMin=start_datetime,
            timeMax=end_datetime,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter and format conflicts
        conflicts = []
        for event in events:
            # Skip all-day events or declined events
            if event.get('start').get('date'):  # All-day event
                continue
            
            attendee_response = None
            if 'attendees' in event:
                for attendee in event['attendees']:
                    if attendee.get('email') == user_email:
                        attendee_response = attendee.get('responseStatus')
                        break
            
            # Skip if user declined
            if attendee_response == 'declined':
                continue
            
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
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


def format_conflicts_message(conflicts: List[Dict[str, Any]]) -> str:
    """Format conflicts into a user-friendly message"""
    if not conflicts:
        return "No calendar conflicts found."
    
    message = f"⚠️ Found {len(conflicts)} meeting(s) during your leave dates:\n\n"
    
    for i, conflict in enumerate(conflicts, 1):
        start_dt = datetime.fromisoformat(conflict['start'].replace('Z', '+00:00'))
        summary = conflict.get('summary', 'Untitled Event')
        location = conflict.get('location', '')
        
        message += f"{i}. **{summary}**\n"
        message += f"   📅 {start_dt.strftime('%B %d, %Y at %I:%M %p')}\n"
        if location:
            message += f"   📍 {location}\n"
        message += "\n"
    
    message += "Would you like to proceed with the leave request anyway, or choose different dates?"
    return message

