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
from agents.utils.user_context import get_user_context_from_db, set_user_chat_id

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
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_KEY_FILE", "./server/service-account-key.json")

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

def send_message_to_space(space_name: str, message_text: str) -> Dict[str, Any]:
    """Send a simple text message to a specific Google Chat space"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Google Chat service not initialized")
    
    try:
        response = chat_service.spaces().messages().create(
            parent=space_name,
            body={'text': message_text}
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
        result = send_message_to_space(request.spaceName, request.message)
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

# Webhook handler for incoming messages
@app.api_route("/chat/webhook", methods=["GET", "POST"])
async def webhook_handler(request: Request):
    # Parse Google Chat event payload
    try:
        event = await request.json()
    except Exception:
        return JSONResponse({"text": "Invalid payload"}, status_code=400)

    # Extract fields safely for both DM and room events
    msg = event.get("message", {}) or {}
    space = msg.get("space", {}) or event.get("space", {}) or {}
    user = msg.get("sender", {}) or event.get("user", {}) or {}

    space_name = space.get("name")  # This is your chat_id (e.g., "spaces/AAAA.../threads/...")
    message_text = msg.get("argumentText") or msg.get("text") or ""
    sender_email = user.get("email") or ""
    sender_display_name = user.get("displayName") or ""

    # Process asynchronously (simple inline await here; could offload to a task queue if needed)
    await process_webhook_message(space_name, message_text, sender_email, sender_display_name)

    # Respond quickly to Chat
    return JSONResponse({"text": "Processing your request..."}, status_code=200)

async def process_webhook_message(space_name: str, message_text: str, sender_email: str, sender_display_name: str = ""):
    """Process webhook message with Mira agent"""
    try:
        print(f"💡 Message: {message_text}")
        print(f"👤 Sender: {sender_display_name} ({sender_email})")
        print(f"💬 Space: {space_name}")

        # 1) Try to find user by chat_id first
        user_context = get_user_context_from_db(email=None, chat_id=space_name)

        # 2) If not found by chat_id, try by email, then persist chat_id
        if not user_context and sender_email:
            email_context = get_user_context_from_db(email=sender_email, chat_id=None)
            if email_context:
                linked = set_user_chat_id(sender_email, space_name)
                if linked:
                    print(f"✅ Stored chat_id for {sender_email}: {space_name}")
                else:
                    print(f"ℹ️ No DB row updated for {sender_email} (check employee table).")
                # Use that context and reflect the current chat_id
                email_context["chat_id"] = space_name
                user_context = email_context

        if not user_context:
            print("⚠️ No user context found by chat_id or email.")
        
        # 3) Route to main agent with user context and chat_id
        agent_response = main_agent(message_text, user_context, space_name)

        # Optionally, echo the response to Chat if chat_service is initialized
        if chat_service and space_name and agent_response:
            try:
                chat_service.spaces().messages().create(
                    parent=space_name,
                    body={'text': agent_response if isinstance(agent_response, str) else json.dumps(agent_response)}
                ).execute()
            except Exception as send_err:
                print(f"❌ Error sending reply to Chat: {send_err}")

    except Exception as error:
        print(f"❌ Error processing webhook message: {error}")
