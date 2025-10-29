import os
import json
import httpx
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Import the main agent
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agents.mira.mira import main_agent
from agents.utils.user_context import get_user_context_from_db

# Load environment variables
load_dotenv()

app = FastAPI(title="Mira - Workplace Assistant Bot", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
PORT = int(os.getenv("PORT", 3005))
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_KEY_FILE", "./service-account-key.json")

SCOPES = [
    "https://www.googleapis.com/auth/chat.bot",
    "https://www.googleapis.com/auth/chat.messages",
    "https://www.googleapis.com/auth/chat.spaces",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# Global variables
auth_client = None
chat_service = None
calendar_service = None

# Pydantic models
class SendMessageRequest(BaseModel):
    spaceName: str
    message: str
    threadName: Optional[str] = None

class BroadcastMessageRequest(BaseModel):
    message: str

class SendCardRequest(BaseModel):
    spaceName: str
    title: str
    subtitle: Optional[str] = None
    text: str
    buttons: Optional[List[Dict[str, str]]] = None

class SendLeaveCardRequest(BaseModel):
    spaceName: str
    employeeEmail: str
    supervisorEmail: str
    requestId: str

class SendApprovalCardRequest(BaseModel):
    requestId: str
    employeeEmail: str
    employeeName: str
    supervisorEmail: str
    supervisorSpace: str
    leaveType: str
    startDate: str
    endDate: str
    reason: str

class WebhookEvent(BaseModel):
    chat: Optional[Dict[str, Any]] = None
    applicationId: Optional[str] = None
    decision: Optional[str] = None

# Initialize Google Auth and Chat service
def initialize_google_services():
    global auth_client, chat_service, calendar_service
    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            auth_client = credentials
            chat_service = build('chat', 'v1', credentials=credentials)
            calendar_service = build('calendar', 'v3', credentials=credentials)
            print("✅ Google Chat and Calendar services initialized successfully")
        else:
            print("❌ Service account file not found")
    except Exception as error:
        print(f"❌ Error loading service account: {error}")
        raise

# Core Google Chat Functions

def send_message_to_space(space_name: str, message_text: str, thread_name: Optional[str] = None) -> Dict[str, Any]:
    """Send a simple text message to a specific Google Chat space"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        body: Dict[str, Any] = {'text': message_text}
        if thread_name:
            body['thread'] = {'name': thread_name}
        response = chat_service.spaces().messages().create(
            parent=space_name,
            body=body
        ).execute()
        
        return {
            "success": True,
            "messageId": response.get('name'),
            "space": space_name,
            "text": message_text
        }
    except Exception as error:
        print(f"❌ Error sending message to space: {error}")
        raise HTTPException(status_code=500, detail=str(error))

def broadcast_message_to_all(message_text: str) -> Dict[str, Any]:
    """Broadcast a message to all available Google Chat spaces"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        # List all spaces
        spaces_result = chat_service.spaces().list(pageSize=100).execute()
        spaces = spaces_result.get('spaces', [])
        
        results = []
        for space in spaces:
            try:
                response = chat_service.spaces().messages().create(
                    parent=space['name'],
                    body={'text': message_text}
                ).execute()
                results.append({
                    "space": space['name'],
                    "spaceType": space.get('spaceType'),
                    "success": True,
                    "messageId": response.get('name')
                })
            except Exception as space_error:
                results.append({
                    "space": space['name'],
                    "spaceType": space.get('spaceType'),
                    "success": False,
                    "error": str(space_error)
                })
        
        return {
            "success": True,
            "totalSpaces": len(spaces),
            "successfulSends": len([r for r in results if r['success']]),
            "results": results
        }
    except Exception as error:
        print(f"❌ Error broadcasting message: {error}")
        raise HTTPException(status_code=500, detail=str(error))

def send_card(space_name: str, title: str, subtitle: str = None, text: str = "", buttons: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Send a rich card message to a specific Google Chat space"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        # Build the card structure
        card = {
            "cards": [{
                "header": {
                    "title": title,
                    "subtitle": subtitle or ""
                },
                "sections": [{
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": text
                            }
                        }
                    ]
                }]
            }]
        }
        
        # Add buttons if provided
        if buttons:
            button_widgets = []
            for button in buttons:
                button_widgets.append({
                    "buttons": [{
                        "textButton": {
                            "text": button.get("text", "Button"),
                            "onClick": {
                                "openLink": {
                                    "url": button.get("url", "#")
                                }
                            }
                        }
                    }]
                })
            
            if button_widgets:
                card["cards"][0]["sections"].append({
                    "widgets": button_widgets
                })
        
        response = chat_service.spaces().messages().create(
            parent=space_name,
            body=card
        ).execute()
        
        return {
            "success": True,
            "messageId": response.get('name'),
            "space": space_name,
            "card": card
        }
    except Exception as error:
        print(f"❌ Error sending card: {error}")
        raise HTTPException(status_code=500, detail=str(error))

def send_leave_request_card(space_name: str, employee_email: str, supervisor_email: str, request_id: str) -> Dict[str, Any]:
    """Send an interactive leave request card with form widgets to a specific Google Chat space"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        # Build a card with structured input fields using textParagraph and buttons
        card = {
            "cards": [{
                "header": {
                    "title": "Leave Request Form",
                    "subtitle": f"Request ID: {request_id}"
                },
                "sections": [{
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": f"<b>Employee:</b> {employee_email}<br><b>Supervisor:</b> {supervisor_email}<br><br>Please provide your leave details in the following format:"
                            }
                        }
                    ]
                }, {
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": "<b>📋 Leave Request Format:</b><br><br>" +
                                       "<b>Leave Type:</b> Annual, Sick, Personal, Medical, or Other<br>" +
                                       "<b>Start Date:</b> YYYY-MM-DD (e.g., 2024-01-15)<br>" +
                                       "<b>End Date:</b> YYYY-MM-DD (e.g., 2024-01-20)<br>" +
                                       "<b>Reason:</b> Brief description of your leave request<br><br>" +
                                       "<b>Example:</b><br>" +
                                       "Leave Type: Annual<br>" +
                                       "Start Date: 2024-01-15<br>" +
                                       "End Date: 2024-01-20<br>" +
                                       "Reason: Family vacation"
                            }
                        }
                    ]
                }, {
                    "widgets": [
                        {
                            "buttons": [{
                                "textButton": {
                                    "text": "📝 Submit Leave Details",
                                    "onClick": {
                                        "action": {
                                            "actionMethodName": "SUBMIT_LEAVE_REQUEST",
                                            "parameters": [
                                                {"key": "request_id", "value": request_id},
                                                {"key": "employee_email", "value": employee_email},
                                                {"key": "supervisor_email", "value": supervisor_email}
                                            ]
                                        }
                                    }
                                }
                            }]
                        }
                    ]
                }]
            }]
        }
        
        response = chat_service.spaces().messages().create(
            parent=space_name,
            body=card
        ).execute()
        
        return {
            "success": True,
            "messageId": response.get('name'),
            "space": space_name,
            "request_id": request_id,
            "card": card
        }
    except Exception as error:
        print(f"❌ Error sending leave request card: {error}")
        raise HTTPException(status_code=500, detail=str(error))

def send_supervisor_approval_card(
    supervisor_space: str,
    request_id: str,
    employee_name: str,
    employee_email: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str
) -> Dict[str, Any]:
    """Send an interactive leave approval card to supervisor with approve/decline buttons"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        print(f"\n🎴 Building approval card structure...")
        # Build approval card with approve and decline buttons
        # Build card with proper Google Chat API format
        # Format: Use keyValue and textParagraph widgets
        card = {
            "cards": [{
                "header": {
                    "title": "Leave Request Approval",
                    "subtitle": f"Request ID: {request_id}"
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "keyValue": {
                                    "topLabel": "Employee",
                                    "content": f"{employee_name} ({employee_email})"
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Leave Type",
                                    "content": leave_type
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Start Date",
                                    "content": start_date
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "End Date",
                                    "content": end_date
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Reason",
                                    "content": reason
                                }
                            }
                        ]
                    },
                    {
                        "widgets": [
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": "Approve",
                                            "onClick": {
                                                "openLink": {
                                                    "url": os.getenv("PUBLIC_WEBHOOK_URL", "http://localhost:3005") + f"/chat/process-approval?request_id={request_id}&action=APPROVE&space={supervisor_space}"
                                                }
                                            }
                                        }
                                    },
                                    {
                                        "textButton": {
                                            "text": "Decline",
                                            "onClick": {
                                                "openLink": {
                                                    "url": os.getenv("PUBLIC_WEBHOOK_URL", "http://localhost:3005") + f"/chat/process-approval?request_id={request_id}&action=DECLINE&space={supervisor_space}"
                                                }
                                            }
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }]
        }
        
        print(f"✅ Card structure built successfully")
        print(f"   Card sections: {len(card['cards'][0]['sections'])}")
        print(f"   Action buttons: 2 (Approve/Decline)")
        print(f"   Target space: {supervisor_space}")
        
        print(f"\n🚀 Sending card to Google Chat API...")
        response = chat_service.spaces().messages().create(
            parent=supervisor_space,
            body=card
        ).execute()
        
        message_id = response.get('name')
        print(f"✅ Card sent successfully!")
        print(f"   Message ID: {message_id}")
        print(f"   Space: {supervisor_space}")
        print(f"   Request ID: {request_id}")
        
        return {
            "success": True,
            "messageId": message_id,
            "space": supervisor_space,
            "request_id": request_id,
            "card": card
        }
    except Exception as error:
        print(f"\n❌ ERROR: Failed to send supervisor approval card")
        print(f"   Error: {error}")
        print(f"   Space: {supervisor_space}")
        print(f"   Request ID: {request_id}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(error))

# Startup event
@app.on_event("startup")
async def startup_event():
    initialize_google_services()
    print("🚀 Mira Workplace Assistant Bot started successfully")
    print("🤖 Agent capabilities:")
    print("   - Policy document search")
    print("   - HR task assistance")
    print("   - IT support")
    print("   - Resource management")

# Health check
@app.get("/")
async def health_check():
    return {"success": True, "message": "Mira Bot is running"}

# List spaces
@app.get("/chat/spaces")
async def list_spaces():
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        spaces_result = chat_service.spaces().list(pageSize=100).execute()
        return {
            "success": True,
            "spaces": spaces_result.get('spaces', [])
        }
    except Exception as error:
        print(f"❌ Error listing spaces: {error}")
        raise HTTPException(status_code=500, detail=str(error))

# Send message to space
@app.post("/chat/send")
async def send_message(request: SendMessageRequest):
    try:
        result = send_message_to_space(request.spaceName, request.message, request.threadName)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Error in send message endpoint: {error}")
        raise HTTPException(status_code=500, detail=str(error))

# Broadcast message to all spaces
@app.post("/chat/broadcast")
async def broadcast_message(request: BroadcastMessageRequest):
    try:
        result = broadcast_message_to_all(request.message)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Error in broadcast endpoint: {error}")
        raise HTTPException(status_code=500, detail=str(error))

# Send card to space
@app.post("/chat/send-card")
async def send_card_endpoint(request: SendCardRequest):
    try:
        result = send_card(
            space_name=request.spaceName,
            title=request.title,
            subtitle=request.subtitle,
            text=request.text,
            buttons=request.buttons
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Error in send card endpoint: {error}")
        raise HTTPException(status_code=500, detail=str(error))

# Send leave request card to space
@app.post("/chat/send-leave-card")
async def send_leave_card_endpoint(request: SendLeaveCardRequest):
    try:
        result = send_leave_request_card(
            space_name=request.spaceName,
            employee_email=request.employeeEmail,
            supervisor_email=request.supervisorEmail,
            request_id=request.requestId
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Error in send leave card endpoint: {error}")
        raise HTTPException(status_code=500, detail=str(error))

# Send supervisor approval card
@app.post("/chat/send-approval-card")
async def send_approval_card_endpoint(request: SendApprovalCardRequest):
    try:
        print(f"\n{'='*70}")
        print(f"📨 RECEIVED: Send Approval Card API Request")
        print(f"{'='*70}")
        print(f"   Request ID: {request.requestId}")
        print(f"   Employee: {request.employeeName} ({request.employeeEmail})")
        print(f"   Supervisor: {request.supervisorEmail}")
        print(f"   Supervisor Space: {request.supervisorSpace}")
        print(f"   Leave Type: {request.leaveType}")
        print(f"   Dates: {request.startDate} to {request.endDate}")
        print(f"   Reason: {request.reason}")
        print(f"{'='*70}\n")
        
        result = send_supervisor_approval_card(
            supervisor_space=request.supervisorSpace,
            request_id=request.requestId,
            employee_name=request.employeeName,
            employee_email=request.employeeEmail,
            leave_type=request.leaveType,
            start_date=request.startDate,
            end_date=request.endDate,
            reason=request.reason
        )
        
        print(f"\n{'='*70}")
        print(f"✅ RESPONSE: Approval card sent successfully")
        print(f"   Message ID: {result.get('messageId')}")
        print(f"   Space: {result.get('space')}")
        print(f"{'='*70}\n")
        
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as error:
        print(f"\n{'='*70}")
        print(f"❌ ERROR: Failed to send approval card")
        print(f"   Error: {error}")
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=str(error))

# Process approval/decline from button clicks
@app.get("/chat/process-approval")
async def process_approval_button(request: Request):
    """Process approval/decline when button is clicked - receives GET request with query params"""
    from fastapi.responses import HTMLResponse
    
    try:
        request_id = request.query_params.get("request_id")
        action = request.query_params.get("action")
        space = request.query_params.get("space")
        
        print(f"\n{'='*70}")
        print(f"🎯 Button Click Received!")
        print(f"   Request ID: {request_id}")
        print(f"   Action: {action}")
        print(f"   Space: {space}")
        print(f"{'='*70}\n")
        
        if not request_id or not action:
            return HTMLResponse(content="""
                <html><body>
                    <h1>Error</h1>
                    <p>Missing parameters. Please close this window.</p>
                </body></html>
            """)
        
        # Import database utilities
        from agents.utils import db_util
        
        # Get leave request
        leave_request = db_util.get_leave_request(request_id)
        
        if not leave_request:
            return HTMLResponse(content="""
                <html><body>
                    <h1>Request Not Found</h1>
                    <p>Leave request not found in database. Please close this window.</p>
                </body></html>
            """)
        
        # Update status
        new_status = "APPROVED" if action == "APPROVE" else "DECLINED"
        decision_note = f"Leave request {new_status.lower()} by supervisor"
        
        success = db_util.update_leave_request_status(request_id, new_status, decision_note)
        
        if not success:
            return HTMLResponse(content="""
                <html><body>
                    <h1>Database Error</h1>
                    <p>Failed to update database. Please close this window.</p>
                </body></html>
            """)
        
        # Send notifications
        employee_space = leave_request.get("employee_space")
        employee_email = leave_request.get("employee_email")
        
        if employee_space:
            notification_msg = f"Your leave request ({request_id}) has been {new_status.lower()} by your supervisor."
            send_message_to_space(employee_space, notification_msg)
            print(f"✅ Notified employee: {employee_email}")
        
        confirmation_msg = f"Leave request {request_id} has been {new_status.lower()} and employee has been notified."
        if space:
            send_message_to_space(space, confirmation_msg)
            print(f"✅ Sent confirmation to supervisor")
        
        print(f"\n{'='*70}")
        print(f"✅ {new_status} complete!")
        print(f"{'='*70}\n")
        
        # Return success page
        return HTMLResponse(content=f"""
            <html>
                <head>
                    <title>Leave Request {new_status}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        h1 {{ color: #34A853; }}
                        .success {{ background: #f0f9ff; padding: 20px; border-radius: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="success">
                        <h1>✓ Leave Request {new_status}</h1>
                        <p>Request ID: {request_id}</p>
                        <p>The employee has been notified.</p>
                        <p><small>You can close this window.</small></p>
                    </div>
                </body>
            </html>
        """)
        
    except Exception as error:
        print(f"❌ Error processing approval button: {error}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"""
            <html><body>
                <h1>Error</h1>
                <p>An error occurred: {str(error)}</p>
                <p>Please close this window.</p>
            </body></html>
        """)

async def process_incoming_event(body_bytes: bytes):
    """Parse the incoming event and route to appropriate handlers with minimal latency in the webhook."""
    try:
        event = json.loads(body_bytes.decode('utf-8') or '{}')

        # Quick classification log without heavy pretty-printing
        evt_type = event.get('type') or event.get('action', {}).get('actionMethodName') or 'unknown'
        print(f"🔎 Processing event type={evt_type}")

        # Card button interactions
        action_response = event.get("action", {})
        if action_response and action_response.get("actionMethodName"):
            await process_card_button_action(event)
            return

        # Regular message events
        space_name = (
            event.get("chat", {}).get("messagePayload", {}).get("space", {}).get("name") or
            event.get("space", {}).get("name") or
            event.get("chat", {}).get("space", {}).get("name")
        )
        message_text = (
            event.get("chat", {}).get("messagePayload", {}).get("message", {}).get("text") or
            event.get("message", {}).get("text")
        )
        thread_name = (
            (event.get("message", {}) or {}).get("thread", {}).get("name") or
            (event.get("chat", {}).get("messagePayload", {}).get("message", {}) or {}).get("thread", {}).get("name")
        )
        sender_info = (
            event.get("chat", {}).get("messagePayload", {}).get("message", {}).get("sender", {}) or
            event.get("message", {}).get("sender", {})
        )
        sender_email = sender_info.get("email")
        sender_type = sender_info.get("type")
        sender_display_name = sender_info.get("displayName", "")

        if not space_name or not message_text:
            print("⚠️ Missing space or message text; dropping event")
            return

        if sender_type == "BOT":
            print("🤖 Skipping bot-originated message")
            return

        await process_webhook_message(space_name, message_text, sender_email, sender_display_name, thread_name)

    except Exception as error:
        print(f"❌ Error in process_incoming_event: {error}")

# Webhook handler for incoming messages
@app.api_route("/chat/webhook", methods=["GET", "POST"])
async def webhook_handler(request: Request):
    try:
        # Handle GET requests (for testing)
        if request.method == "GET":
            return {"success": True, "message": "Webhook endpoint is active"}
        
        # Handle POST requests (incoming messages) - read body and offload processing
        # Always respond immediately with a short placeholder to avoid timeout banner
        response = JSONResponse(content={"text": "Got it — working on it..."}, status_code=200)

        body_bytes = await request.body()
        print("🔔 Webhook event received")

        import asyncio
        asyncio.create_task(process_incoming_event(body_bytes))

        return response
        
    except Exception as error:
        print(f"❌ Failed to process webhook: {error}")
        return JSONResponse(content={}, status_code=200)

 
async def process_card_button_action(event: Dict[str, Any]):
    """Process card button click actions (approve/decline leave requests)"""
    try:
        action_response = event.get("action", {})
        action_method = action_response.get("actionMethodName")
        parameters = action_response.get("parameters", [])
        
        # Extract request_id and employee_email from parameters
        param_dict = {p.get("key"): p.get("value") for p in parameters}
        request_id = param_dict.get("request_id")
        employee_email = param_dict.get("employee_email")
        
        print(f"🎯 Processing {action_method} for request {request_id}")
        
        # Import database utilities
        from agents.utils import db_util
        
        # Get leave request details
        leave_request = db_util.get_leave_request(request_id)
        
        if not leave_request:
            print(f"❌ Leave request {request_id} not found")
            return
        
        # Determine new status based on action
        if action_method == "APPROVE_LEAVE":
            new_status = "APPROVED"
            decision_note = "Leave request approved by supervisor"
        elif action_method == "DECLINE_LEAVE":
            new_status = "DECLINED"
            decision_note = "Leave request declined by supervisor"
        else:
            print(f"❌ Unknown action method: {action_method}")
            return
        
        # Update leave request status in database
        success = db_util.update_leave_request_status(request_id, new_status, decision_note)
        
        if not success:
            print(f"❌ Failed to update leave request status")
            return
        
        # Get supervisor space and employee space
        # Try multiple paths for space name in different event formats
        supervisor_space = (
            event.get("chat", {}).get("space", {}).get("name") or
            event.get("space", {}).get("name") or
            event.get("action", {}).get("event", {}).get("space", {}).get("name")
        )
        employee_space = leave_request.get("employee_space")
        
        # Update the card in supervisor's space to show decision
        try:
            message_id = event.get("action", {}).get("message", {}).get("name")
            if message_id and supervisor_space:
                # Update the card to show decision
                updated_card = {
                    "cards": [{
                        "header": {
                            "title": "Leave Request Approval",
                            "subtitle": f"Request ID: {request_id}"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "keyValue": {
                                            "topLabel": "Status",
                                            "content": f"{new_status}"
                                        }
                                    },
                                    {
                                        "keyValue": {
                                            "topLabel": "Employee",
                                            "content": f"{employee_email}"
                                        }
                                    }
                                ]
                            }
                        ]
                    }]
                }
                
                # Update the message in supervisor's space
                chat_service.spaces().messages().update(
                    name=message_id,
                    body=updated_card
                ).execute()
                
                print(f"✅ Updated card in supervisor space")
        except Exception as card_error:
            print(f"⚠️ Could not update card: {card_error}")
        
        # Send notification to employee's space
        if employee_space:
            notification_message = f"Your leave request ({request_id}) has been {new_status.lower()}"
            try:
                send_message_to_space(employee_space, notification_message)
                print(f"✅ Notified employee in space {employee_space}")
            except Exception as notify_error:
                print(f"⚠️ Could not notify employee: {notify_error}")
        
        # Also send notification back to supervisor's space
        if supervisor_space:
            confirmation_message = f"Leave request {request_id} has been {new_status.lower()} and employee has been notified."
            try:
                send_message_to_space(supervisor_space, confirmation_message)
            except Exception as confirm_error:
                print(f"⚠️ Could not send confirmation: {confirm_error}")
        
    except Exception as error:
        print(f"❌ Failed to process card button action: {error}")

async def process_webhook_message(space_name: str, message_text: str, sender_email: str, sender_display_name: str = "", thread_name: Optional[str] = None):
    """Process webhook message with Mira agent"""
    try:
        print(f"💡 Processing message with Mira: \"{message_text}\"")
        print(f"👤 From: {sender_display_name} ({sender_email})")
        
        # Retrieve user context from database
        user_context = get_user_context_from_db(sender_email, space_name)
        if user_context:
            print(f"✅ Found user context: {user_context.get('emp_name', 'Unknown')} ({user_context.get('designation', 'Unknown')})")
        else:
            print(f"⚠️ No user context found for {sender_email}")
        
        # Get response from Mira agent with user context and space name
        agent_response = main_agent(message_text, user_context, space_name)
        
        if agent_response:
            print(f"💬 Sending Mira response to {space_name}...")
            
            # Send response using internal API
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": agent_response,
                    "threadName": thread_name
                })
            
            print(f"✅ Replied to {space_name} with Mira's response.")
        else:
            print("❌ No response from Mira agent")
            
            # Send fallback message
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": "I'm sorry, I couldn't process your request. Please try again.",
                    "threadName": thread_name
                })
    
    except Exception as error:
        print(f"❌ Failed to process webhook message: {error}")
        
        # Send error message
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
                    "threadName": thread_name
                })
        except Exception as send_error:
            print(f"❌ Failed to send error message: {send_error}")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Mira Workplace Assistant Bot...")
    print(f"📡 Server will run on http://localhost:{PORT}")
    print("")
    print("📡 Available Endpoints:")
    print("   GET  /                        → Health check")
    print("   GET  /chat/spaces             → List all spaces")
    print("   POST /chat/send               → Send message to space")
    print("   POST /chat/broadcast          → Broadcast to all spaces")
    print("   POST /chat/send-card          → Send rich card to space")
    print("   POST /chat/send-leave-card    → Send interactive leave request card")
    print("   POST /chat/webhook            → Handle incoming messages")
    print("")
    print("💬 Mira is ready to help with:")
    print("   - Company policy questions")
    print("   - HR assistance")
    print("   - IT support")
    print("   - Resource management")
    print("   - General workplace queries")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)
