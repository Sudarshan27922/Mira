# Logging Guide for Leave Approval Workflow

This document explains all the logging added to track the leave approval workflow from start to finish.

## Overview

Comprehensive logging has been added at every step of the workflow to help you:

- Track the complete flow from employee request to supervisor approval
- Debug any issues quickly
- Verify that cards are being sent properly
- Monitor database operations

## Log Output Format

### Success Messages

- ✅ Green checkmark indicates successful operation
- ❌ Red X indicates error/failure
- 📋 Data retrieval operations
- 🚀 Sending/transmission operations
- 💾 Database operations
- 📨 API requests

### Structured Log Sections

Each major step is wrapped in separator lines:

```
======================================================================
```

This makes it easy to find sections in the logs.

## Complete Log Flow

### 1. Employee Sends Leave Request

**Location**: Server receives webhook

```
🔔 Incoming webhook event: {...}
💡 Processing message with Mira: "I need leave..."
👤 From: John Doe (john@example.com)
✅ Found user context: John Doe (Engineer)
```

### 2. HR Agent Processes Request

**Location**: HR tools → `leave_process_workflow()`

```
💾 DATABASE: Creating leave request...
   Request ID: req_12345678
   Employee: john@example.com
   Supervisor: supervisor@example.com
   Status: PENDING
   INSERT: Creating new leave request record
✅ DATABASE: Created new leave request successfully
```

### 3. Supervisor Approval Workflow Starts

**Location**: HR tools → `send_supervisor_approval()`

```
======================================================================
📤 STEP 1: Starting supervisor approval workflow
   Request ID: req_12345678
   Supervisor Email: supervisor@example.com
======================================================================

📋 STEP 2: Retrieving leave request from database...
✅ Retrieved leave request:
   Employee: john@example.com
   Leave Type: Annual
   Dates: 2025-01-15 to 2025-01-20
   Current Status: PENDING

🔍 STEP 3: Looking up supervisor information...
   Searching for: supervisor@example.com
✅ Found supervisor:
   Name: Jane Smith
   Email: supervisor@example.com
   Chat ID: spaces/BBBBBBBBBBB

👤 STEP 4: Retrieving employee information...
✅ Employee: John Doe (john@example.com)

📨 STEP 5: Preparing to send approval card...
   API Endpoint: http://localhost:3005/chat/send-approval-card
   Target Space: spaces/BBBBBBBBBBB
   Card Details:
      - Employee: John Doe (john@example.com)
      - Leave Type: Annual
      - Dates: 2025-01-15 to 2025-01-20
      - Reason: Vacation

🚀 STEP 6: Sending approval card to supervisor...
```

### 4. API Endpoint Receives Request

**Location**: Server → `/chat/send-approval-card`

```
======================================================================
📨 RECEIVED: Send Approval Card API Request
======================================================================
   Request ID: req_12345678
   Employee: John Doe (john@example.com)
   Supervisor: supervisor@example.com
   Supervisor Space: spaces/BBBBBBBBBBB
   Leave Type: Annual
   Dates: 2025-01-15 to 2025-01-20
   Reason: Vacation
======================================================================

🎴 Building approval card structure...
✅ Card structure built successfully
   Card sections: 2
   Action buttons: 2 (Approve/Decline)
   Target space: spaces/BBBBBBBBBBB

🚀 Sending card to Google Chat API...
✅ Card sent successfully!
   Message ID: spaces/BBBBBBBBBBB/messages/1234567890
   Space: spaces/BBBBBBBBBBB
   Request ID: req_12345678

======================================================================
✅ RESPONSE: Approval card sent successfully
   Message ID: spaces/BBBBBBBBBBB/messages/1234567890
   Space: spaces/BBBBBBBBBBB
======================================================================
```

### 5. Success Confirmation

**Location**: HR tools → `send_supervisor_approval()`

```
✅ SUCCESS: Approval card sent to supervisor!
   Message ID: spaces/BBBBBBBBBBB/messages/1234567890
   Space: spaces/BBBBBBBBBBB
   Request ID: req_12345678

======================================================================
✅ Leave approval workflow completed successfully
======================================================================
```

### 6. Supervisor Clicks Button

**Location**: Server → `webhook_handler()` → `process_card_button_action()`

```
🔔 Incoming webhook event: {...}
🎯 Card button action detected
🎯 Processing APPROVE_LEAVE for request req_12345678
✅ Updated card in supervisor space
✅ Notified employee in space spaces/AAAAAAAAAAA
✅ Sent confirmation to supervisor
```

## Reading the Logs

### Quick Success Check

Look for:

```
✅ Leave approval workflow completed successfully
```

This indicates the entire workflow completed without errors.

### Finding Errors

Look for:

```
❌ ERROR: ...
```

Common error patterns:

1. **Database connection**:

   ```
   ❌ DATABASE ERROR: Failed to create leave request: ...
   ```

2. **Supervisor not found**:

   ```
   ❌ Supervisor supervisor@example.com not found in database
   ❌ Supervisor has no chat_id configured
   ```

3. **Card sending failed**:
   ```
   ❌ ERROR: Failed to send supervisor approval card
   ❌ Failed to send approval card: ...
   ```

### Tracking Specific Requests

Find a request by searching for:

```
Request ID: req_12345678
```

This appears in every log message related to that request.

## Log Locations

### HR Tools Logs

- File: `agents/mira/sub_agents/hr/tools.py`
- Shows: Supervisor lookup, database queries, API calls

### Server Logs

- File: `server/main.py`
- Shows: API requests, card building, Google Chat API calls

### Database Logs

- File: `agents/utils/db_util.py`
- Shows: Insert/update operations, query results

## Example Complete Log Output

Here's what a complete successful workflow looks like:

```
💡 Processing message with Mira: "I need annual leave from 2025-01-15 to 2025-01-20"
👤 From: John Doe (john@example.com)
✅ Found user context: John Doe (Engineer)

💾 DATABASE: Creating leave request...
   Request ID: req_87654321
   Employee: john@example.com
   Supervisor: supervisor@example.com
   Status: PENDING
   INSERT: Creating new leave request record
✅ DATABASE: Created new leave request successfully

======================================================================
📤 STEP 1: Starting supervisor approval workflow
   Request ID: req_87654321
   Supervisor Email: supervisor@example.com
======================================================================

📋 STEP 2: Retrieving leave request from database...
✅ Retrieved leave request:
   Employee: john@example.com
   Leave Type: Annual
   Dates: 2025-01-15 to 2025-01-20
   Current Status: PENDING

🔍 STEP 3: Looking up supervisor information...
   Searching for: supervisor@example.com
✅ Found supervisor:
   Name: Jane Smith
   Email: supervisor@example.com
   Chat ID: spaces/BBBBBBBBBBB

👤 STEP 4: Retrieving employee information...
✅ Employee: John Doe (john@example.com)

📨 STEP 5: Preparing to send approval card...
   API Endpoint: http://localhost:3005/chat/send-approval-card
   Target Space: spaces/BBBBBBBBBBB
   Card Details:
      - Employee: John Doe (john@example.com)
      - Leave Type: Annual
      - Dates: 2025-01-15 to 2025-01-20
      - Reason: Vacation

🚀 STEP 6: Sending approval card to supervisor...
======================================================================
📨 RECEIVED: Send Approval Card API Request
======================================================================
   Request ID: req_87654321
   Employee: John Doe (john@example.com)
   Supervisor: supervisor@example.com
   Supervisor Space: spaces/BBBBBBBBBBB
   Leave Type: Annual
   Dates: 2025-01-15 to 2025-01-20
   Reason: Vacation
======================================================================

🎴 Building approval card structure...
✅ Card structure built successfully
   Card sections: 2
   Action buttons: 2 (Approve/Decline)
   Target space: spaces/BBBBBBBBBBB

🚀 Sending card to Google Chat API...
✅ Card sent successfully!
   Message ID: spaces/BBBBBBBBBBB/messages/987654321
   Space: spaces/BBBBBBBBBBB
   Request ID: req_87654321

======================================================================
✅ RESPONSE: Approval card sent successfully
   Message ID: spaces/BBBBBBBBBBB/messages/987654321
   Space: spaces/BBBBBBBBBBB
======================================================================

✅ SUCCESS: Approval card sent to supervisor!
   Message ID: spaces/BBBBBBBBBBB/messages/987654321
   Space: spaces/BBBBBBBBBBB
   Request ID: req_87654321

======================================================================
✅ Leave approval workflow completed successfully
======================================================================
```

## Tips for Monitoring

1. **Real-time monitoring**: Watch terminal output while testing
2. **Search for errors**: Use `grep` to find all errors: `grep "❌" logs.txt`
3. **Track workflow**: Search for request ID to follow a specific request
4. **Check supervisor lookup**: Look for "STEP 3" to verify supervisor found
5. **Verify card sending**: Look for "STEP 6" to confirm card sent

## Common Issues and Log Patterns

### Issue: Supervisor not found

```
🔍 STEP 3: Looking up supervisor information...
   Searching for: supervisor@example.com
❌ Supervisor supervisor@example.com not found in database
```

**Solution**: Add supervisor to employee table with correct email.

### Issue: No chat_id configured

```
✅ Found supervisor:
   Name: Jane Smith
   Email: supervisor@example.com
❌ Supervisor has no chat_id configured
```

**Solution**: Set chat_id in employee table for the supervisor.

### Issue: Card sending failed

```
🚀 STEP 6: Sending approval card to supervisor...
❌ FAILED: Could not send approval card
   Error: {...}
```

**Solution**: Check Google Chat API credentials and supervisor space access.

## Summary

With these comprehensive logs, you can:

- ✅ See exactly when approval cards are sent
- ✅ Verify supervisor lookup is working
- ✅ Track database operations
- ✅ Debug issues quickly
- ✅ Monitor the complete workflow

All logs are printed to the server console and provide detailed information about each step of the leave approval process.
