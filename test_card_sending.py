"""
Unit test for supervisor approval card sending
Tests the API endpoint with actual data to verify card is sent
"""

import requests
import json
import sys

def test_send_approval_card():
    """Test sending approval card with the actual data from logs"""
    
    print("\n" + "="*70)
    print("🧪 TESTING: Supervisor Approval Card Sending")
    print("="*70 + "\n")
    
    # Test data from the logs
    test_data = {
        "requestId": "req_6480110",
        "employeeEmail": "meniduj@mitrai.com",
        "employeeName": "Menidu",
        "supervisorEmail": "meniduj@mitrai.com",
        "supervisorSpace": "spaces/_nXSAiAAAAE",
        "leaveType": "casual leave",
        "startDate": "2025-10-27",
        "endDate": "2025-10-28",
        "reason": "family commitment"
    }
    
    print("📋 Test Data:")
    print(f"   Request ID: {test_data['requestId']}")
    print(f"   Employee: {test_data['employeeName']} ({test_data['employeeEmail']})")
    print(f"   Supervisor Space: {test_data['supervisorSpace']}")
    print(f"   Leave Type: {test_data['leaveType']}")
    print(f"   Dates: {test_data['startDate']} to {test_data['endDate']}")
    print(f"   Reason: {test_data['reason']}")
    
    # Test endpoint
    port = 3005
    url = f"http://localhost:{port}/chat/send-approval-card"
    
    print(f"\n🚀 Sending POST request to: {url}")
    print(f"{'='*70}\n")
    
    try:
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"📨 Response Status: {response.status_code}")
        print(f"📨 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success Response:")
            print(json.dumps(result, indent=2))
            
            if result.get("success"):
                print(f"\n{'='*70}")
                print("✅ TEST PASSED: Card sent successfully!")
                print(f"   Message ID: {result.get('messageId')}")
                print(f"   Space: {result.get('space')}")
                print(f"{'='*70}\n")
                return True
            else:
                print(f"\n❌ TEST FAILED: Response indicates failure")
                print(f"   Error: {result}")
                return False
        else:
            print(f"\n❌ TEST FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ TEST FAILED: Could not connect to server")
        print(f"   Make sure the server is running on port {port}")
        return False
        
    except requests.exceptions.Timeout:
        print(f"❌ TEST FAILED: Request timed out")
        print(f"   Server may be stuck or unresponsive")
        return False
        
    except Exception as e:
        print(f"❌ TEST FAILED: Unexpected error")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_health():
    """Test if server is running"""
    try:
        response = requests.get("http://localhost:3005/", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
    except:
        print("❌ Server is not responding")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 SUPERVISOR APPROVAL CARD UNIT TEST")
    print("="*70)
    
    # Check server health
    if not test_server_health():
        print("\n⚠️  Make sure the server is running before running this test")
        sys.exit(1)
    
    # Run the test
    success = test_send_approval_card()
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)

