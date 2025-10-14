#!/usr/bin/env python3
"""
Setup script for Google Chat integration
This script helps you set up the necessary Google Chat API credentials
"""

import os
import json
from pathlib import Path

def create_service_account_template():
    """Create a template service account key file"""
    template = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
        "client_email": "your-service-account@your-project-id.iam.gserviceaccount.com",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"
    }
    
    template_path = Path("service-account-key.json.template")
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✅ Created service account template: {template_path}")
    print("📝 Please:")
    print("   1. Copy this file to 'service-account-key.json'")
    print("   2. Replace the placeholder values with your actual Google Cloud credentials")
    print("   3. Make sure your service account has Google Chat API enabled")

def create_env_file():
    """Create a .env file template"""
    env_content = """# Google Chat Configuration
SERVICE_ACCOUNT_KEY_FILE=./service-account-key.json
PORT=3005

# Add your other environment variables here
# GEMINI_API_KEY=your_gemini_api_key_here
# PINECONE_API_KEY=your_pinecone_api_key_here
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"✅ Created .env file: {env_path}")
    else:
        print(f"ℹ️  .env file already exists: {env_path}")

def print_setup_instructions():
    """Print setup instructions"""
    print("\n" + "="*60)
    print("🚀 GOOGLE CHAT INTEGRATION SETUP")
    print("="*60)
    print("\n1. 📋 PREREQUISITES:")
    print("   - Google Cloud Project with Google Chat API enabled")
    print("   - Service Account with Chat Bot permissions")
    print("   - Python dependencies installed")
    
    print("\n2. 🔧 GOOGLE CLOUD SETUP:")
    print("   a) Go to Google Cloud Console")
    print("   b) Enable Google Chat API")
    print("   c) Create a Service Account")
    print("   d) Download the JSON key file")
    print("   e) Place it as 'service-account-key.json' in the server directory")
    
    print("\n3. 🐍 INSTALL DEPENDENCIES:")
    print("   pip install -r requirements.txt")
    
    print("\n4. 🚀 RUN THE SERVER:")
    print("   cd server")
    print("   python main.py")
    
    print("\n5. 📡 WEBHOOK SETUP:")
    print("   - Set up a webhook URL pointing to: http://your-domain/chat/webhook")
    print("   - Configure it in your Google Chat app settings")
    
    print("\n6. 🧪 TEST ENDPOINTS:")
    print("   - GET  http://localhost:3005/                    (Health check)")
    print("   - GET  http://localhost:3005/chat/spaces         (List spaces)")
    print("   - POST http://localhost:3005/chat/send           (Send message)")
    print("   - POST http://localhost:3005/chat/broadcast      (Broadcast)")
    print("   - POST http://localhost:3005/chat/send-card      (Send card)")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("🔧 Setting up Google Chat integration...")
    
    # Change to server directory
    os.chdir(Path(__file__).parent)
    
    create_service_account_template()
    create_env_file()
    print_setup_instructions()
    
    print("\n✅ Setup complete! Follow the instructions above to configure your Google Chat integration.")
