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
]

# Global variables
auth_client = None
chat_service = None

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
    global auth_client, chat_service
    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            auth_client = credentials
            chat_service = build('chat', 'v1', credentials=credentials)
            print("✅ Google Chat services initialized successfully")
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
    try:
        # Handle GET requests (for testing)
        if request.method == "GET":
            return {"success": True, "message": "Webhook endpoint is active"}
        
        # Handle POST requests (incoming messages)
        event = await request.json()
        print("🔔 Incoming webhook event:", json.dumps(event, indent=2))
        
        # Always respond immediately
        response = JSONResponse(content={}, status_code=200)
        
        # Extract event data
        space_name = event.get("chat", {}).get("messagePayload", {}).get("space", {}).get("name")
        message_text = event.get("chat", {}).get("messagePayload", {}).get("message", {}).get("text")
        sender_info = event.get("chat", {}).get("messagePayload", {}).get("message", {}).get("sender", {})
        sender_email = sender_info.get("email")
        sender_type = sender_info.get("type")
        sender_display_name = sender_info.get("displayName", "")
        
        # Check if this is a card form submission
        action_data = event.get("chat", {}).get("actionMethodName")
        form_inputs = event.get("chat", {}).get("formInputs", {})
        
        if action_data == "SUBMIT_LEAVE_REQUEST":
            print("📝 Processing leave request card submission")
            
            # Extract parameters from action
            action_params = event.get("chat", {}).get("parameters", [])
            request_id = ""
            supervisor_email = ""
            
            for param in action_params:
                if param.get("key") == "request_id":
                    request_id = param.get("value", "")
                elif param.get("key") == "supervisor_email":
                    supervisor_email = param.get("value", "")
            
            print(f"📝 Extracted parameters - Request ID: {request_id}, Supervisor: {supervisor_email}")
            
            # Process in background
            import asyncio
            asyncio.create_task(process_leave_card_submission(
                space_name, 
                form_inputs, 
                sender_email, 
                sender_display_name,
                request_id,
                supervisor_email
            ))
            return response
        
        if not space_name or not message_text:
            print("⚠️ No space name or message text found in event")
            return response
        
        # Skip processing if the message is from the bot itself
        if sender_type == "BOT":
            print("🤖 Skipping bot message")
            return response

        # Process in background
        import asyncio
        asyncio.create_task(process_webhook_message(space_name, message_text, sender_email, sender_display_name))
        
        return response
        
    except Exception as error:
        print(f"❌ Failed to process webhook: {error}")
        return JSONResponse(content={}, status_code=200)

async def process_webhook_message(space_name: str, message_text: str, sender_email: str, sender_display_name: str = ""):
    """Process webhook message with Mira agent"""
    try:
        print(f"💡 Processing message with Mira: \"{message_text}\"")
        print(f"👤 From: {sender_display_name} ({sender_email})")
        
        # Check if this looks like a structured leave request
        leave_data = parse_leave_request_text(message_text)
        if leave_data:
            print(f"📝 Detected structured leave request: {leave_data}")
            
            # Process the leave request directly
            try:
                # Import here to avoid circular imports
                from agents.mira.mira import main_agent
                
                # Create a prompt that includes the space name and complete leave data
                prompt = f"""Space: {space_name}

User: I want to apply for leave with the following details:
- Leave Type: {leave_data['leave_type']}
- Start Date: {leave_data['start_date']}
- End Date: {leave_data['end_date']}
- Reason: {leave_data['reason']}

Please process this leave request."""
                
                # Get user context
                user_context = get_user_context_from_db(sender_email, space_name)
                
                # Process through main agent
                response = main_agent.invoke({
                    "messages": [("user", prompt)],
                    "user_context": user_context
                })
                
                print(f"📝 Main agent response: {response}")
                
                # Send confirmation
                confirmation_message = f"""✅ **Leave Request Processed Successfully**

**Leave Type:** {leave_data['leave_type']}
**Start Date:** {leave_data['start_date']}
**End Date:** {leave_data['end_date']}
**Reason:** {leave_data['reason']}

Your leave request has been submitted and will be processed by your supervisor."""
                
                async with httpx.AsyncClient() as client:
                    await client.post(f"http://localhost:{PORT}/chat/send", json={
                        "spaceName": space_name,
                        "message": confirmation_message
                    })
                
                return
                
            except Exception as agent_error:
                print(f"❌ Error processing leave request through main agent: {agent_error}")
                # Fall through to normal processing
        
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
                    "message": agent_response
                })
            
            print(f"✅ Replied to {space_name} with Mira's response.")
        else:
            print("❌ No response from Mira agent")
            
            # Send fallback message
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": "I'm sorry, I couldn't process your request. Please try again."
                })
    
    except Exception as error:
        print(f"❌ Failed to process webhook message: {error}")
        
        # Send error message
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": "I'm sorry, I'm having trouble processing your request right now. Please try again later."
                })
        except Exception as send_error:
            print(f"❌ Failed to send error message: {send_error}")


def parse_leave_request_text(message_text: str) -> Dict[str, str] | None:
    """Parse structured leave request text and extract fields"""
    try:
        import re
        
        # Normalize the text - remove extra whitespace and convert to lowercase for matching
        text = message_text.strip()
        
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
        
        # Validate that we have all required fields
        required_fields = ['leave_type', 'start_date', 'end_date', 'reason']
        if all(field in extracted for field in required_fields):
            # Clean up the values
            extracted['leave_type'] = extracted['leave_type'].strip()
            extracted['start_date'] = extracted['start_date'].strip()
            extracted['end_date'] = extracted['end_date'].strip()
            extracted['reason'] = extracted['reason'].strip()
            
            # Basic validation
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            if (re.match(date_pattern, extracted['start_date']) and 
                re.match(date_pattern, extracted['end_date'])):
                return extracted
        
        return None
        
    except Exception as e:
        print(f"❌ Error parsing leave request text: {e}")
        return None

async def process_leave_card_submission(space_name: str, form_inputs: Dict[str, Any], sender_email: str, sender_display_name: str = "", request_id: str = "", supervisor_email: str = ""):
    """Process leave request card submission - now prompts user to provide details in text format"""
    try:
        print(f"📝 Processing leave request card submission from {sender_display_name} ({sender_email})")
        
        # Send instructions for providing leave details in text format
        instructions_message = f"""📝 **Leave Request Details Required**

**Request ID:** {request_id}

Please provide your leave details in the following format:

**Leave Type:** Annual, Sick, Personal, Medical, or Other
**Start Date:** YYYY-MM-DD (e.g., 2024-01-15)
**End Date:** YYYY-MM-DD (e.g., 2024-01-20)  
**Reason:** Brief description of your leave request

**Example:**
```
Leave Type: Annual
Start Date: 2024-01-15
End Date: 2024-01-20
Reason: Family vacation
```

Please send your leave details in this exact format."""
        
        async with httpx.AsyncClient() as client:
            await client.post(f"http://localhost:{PORT}/chat/send", json={
                "spaceName": space_name,
                "message": instructions_message
            })
    
    except Exception as error:
        print(f"❌ Failed to process leave card submission: {error}")
        
        # Send error message
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{PORT}/chat/send", json={
                    "spaceName": space_name,
                    "message": "I'm sorry, there was an error processing your leave request. Please try again."
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
