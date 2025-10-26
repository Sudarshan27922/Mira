# Leave Approval Workflow - Complete Flow Explained

## Overview

This document explains the complete leave approval workflow from employee request to final notification, showing how all components work together.

## Complete Workflow

### Phase 1: Employee Initiates Leave Request

**1. Employee sends a message in Google Chat**

```
Employee: "I need to request leave from 2025-01-15 to 2025-01-20 for Annual leave. Reason: Family vacation."
```

**2. Webhook receives and processes message**

- **Location**: `server/main.py` → `webhook_handler()`
- Webhook receives message from Google Chat
- Extracts: `space_name`, `message_text`, `sender_email`
- Calls `get_user_context_from_db(sender_email)` to get:
  - Employee name, email, designation
  - **Manager email** (supervisor email)
  - **Chat ID** (for notifications)

**3. Mira agent routes to HR sub-agent**

- **Location**: `agents/mira/mira.py` → `main_agent()`
- Routes to HR_Agent with user context
- User context includes `manager_email` (supervisor email)

### Phase 2: HR Agent Collects Details

**4. HR agent extracts information**

- **Location**: `agents/mira/sub_agents/hr/agent.py`
- Agent analyzes the message and extracts:
  - Leave type: "Annual"
  - Start date: "2025-01-15"
  - End date: "2025-01-20"
  - Reason: "Family vacation"
  - Employee email: from user context
  - Supervisor email: from `manager_email` in user context
  - Space name: current Google Chat space ID

**5. HR agent calls `leave_process_workflow()`**

- **Location**: `agents/mira/sub_agents/hr/tools.py` → `leave_process_workflow()`
- Validates all required fields are present
- Checks calendar for conflicts
- If conflicts found → asks employee to confirm or change dates
- If no conflicts → proceeds with approval workflow

### Phase 3: Database and Approval Card

**6. Save leave request to database**

- **Location**: `agents/mira/sub_agents/hr/tools.py` → `record_leave_request()`
- **Database**: `agents/utils/db_util.py` → `create_leave_request()`
- Inserts record into `public.leave_requests` table:
  ```sql
  INSERT INTO leave_requests (
    request_id, employee_email, supervisor_email,
    leave_type, start_date, end_date, reason,
    employee_space, status
  ) VALUES (...);
  ```
- Status set to: `PENDING`
- Generates unique `request_id` (e.g., "req_12345678")

**7. Send approval card to supervisor**

- **Location**: `agents/mira/sub_agents/hr/tools.py` → `send_supervisor_approval()`
- **Step 1**: Retrieve leave request from database
- **Step 2**: Get supervisor's chat_id:
  - Query employee table where `emp_email = supervisor_email`
  - Get `chat_id` field
  - **Location**: `agents/utils/user_context.py` → `get_supervisor_info()`
- **Step 3**: Get employee's name from database
- **Step 4**: Call API endpoint `/chat/send-approval-card`
  - **Location**: `server/main.py` → `send_approval_card_endpoint()`
  - Calls `send_supervisor_approval_card()` function

**8. Supervisor receives approval card**

- **Location**: `server/main.py` → `send_supervisor_approval_card()`
- Card is sent to supervisor's Google Chat space
- Card displays:
  - Employee name and email
  - Leave type
  - Start date and end date
  - Reason
  - **Two buttons**: "Approve" and "Decline"
- Buttons include action handlers:
  - `actionMethodName`: "APPROVE_LEAVE" or "DECLINE_LEAVE"
  - `parameters`: request_id, employee_email

### Phase 4: Supervisor Decision

**9. Supervisor clicks Approve or Decline**

- Button click triggers Google Chat webhook
- Event sent to `/chat/webhook`

**10. Webhook processes button action**

- **Location**: `server/main.py` → `webhook_handler()`
- Detects action event (not regular message)
- Extracts:
  - `actionMethodName`: "APPROVE_LEAVE" or "DECLINE_LEAVE"
  - `parameters`: request_id, employee_email
- Calls `process_card_button_action(event)`

**11. Update database status**

- **Location**: `server/main.py` → `process_card_button_action()`
- Gets leave request from database
- Updates status:
  - If Approve → Status: `APPROVED`
  - If Decline → Status: `DECLINED`
- Updates `decision_note` and `approved_at` timestamp
- **Location**: `agents/utils/db_util.py` → `update_leave_request_status()`

**12. Update card in supervisor's space**

- **Location**: `server/main.py` → `process_card_button_action()`
- Updates the card to show decision
- Removes buttons
- Shows status: "✅ APPROVED" or "❌ DECLINED"
- Card becomes read-only

**13. Notify employee**

- **Location**: `server/main.py` → `process_card_button_action()`
- Gets `employee_space` from database record
- Sends message to employee's Google Chat space:
  ```
  Your leave request (req_12345678) has been approved
  ```
  or
  ```
  Your leave request (req_12345678) has been declined
  ```

**14. Send confirmation to supervisor**

- **Location**: `server/main.py` → `process_card_button_action()`
- Sends confirmation message in supervisor's space:
  ```
  Leave request req_12345678 has been approved and employee has been notified.
  ```

## Data Flow Diagram

```
Employee (Google Chat)
    ↓ Message: "I need leave..."
Webhook Handler
    ↓ Extract user context (manager_email)
Mira Agent → HR Sub-Agent
    ↓ Extract leave details
leave_process_workflow()
    ↓ Save to database
Database (leave_requests table)
    ↓ Status: PENDING
send_supervisor_approval()
    ↓ Get supervisor chat_id
    ↓ Call /chat/send-approval-card
send_supervisor_approval_card()
    ↓ Send interactive card
Supervisor (Google Chat)
    ↓ Clicks "Approve" or "Decline"
Webhook (button action)
    ↓ process_card_button_action()
Update Database
    ↓ Status: APPROVED/DECLINED
Update Card (supervisor's space)
    ↓ Show decision
Send Notifications
    ↓ Employee space: "Your request has been approved"
    ↓ Supervisor space: "Employee has been notified"
```

## Database Schema

### employee table (existing, updated)

```sql
CREATE TABLE employee (
    emp_email VARCHAR PRIMARY KEY,
    emp_name VARCHAR,
    manager_email VARCHAR,  -- Supervisor email
    chat_id VARCHAR,         -- Google Chat space ID (NEW FIELD)
    ...other fields
);
```

### leave_requests table (new)

```sql
CREATE TABLE leave_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR UNIQUE,
    employee_email VARCHAR,
    supervisor_email VARCHAR,
    leave_type VARCHAR,
    start_date DATE,
    end_date DATE,
    reason TEXT,
    employee_space VARCHAR,  -- Employee's Google Chat space
    status VARCHAR,          -- PENDING, APPROVED, DECLINED
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    approved_at TIMESTAMP,
    decision_note TEXT
);
```

## Key Integration Points

### 1. User Context Flow

- Employee sends message in Google Chat
- System retrieves their info from database
- Extracts `manager_email` as supervisor email
- Uses this to find supervisor's chat_id

### 2. Supervisor Lookup

- Query: `SELECT chat_id, emp_name FROM employee WHERE emp_email = manager_email`
- Result: Supervisor's Google Chat space ID
- This is where the approval card gets sent

### 3. Database Transaction

- Leave request saved with employee_space
- Supervisor approval updates status
- Employee space stored for later notification

### 4. Webhook Event Handling

- Regular messages → Processed by Mira agent
- Button actions → Processed by `process_card_button_action()`
- Different event structures handled gracefully

## Status Flow

```
PENDING
  ↓
(Calendar conflicts check)
  ↓
PENDING (waiting for supervisor)
  ↓
APPROVED / DECLINED
  ↓
Notifications sent
```

## Error Handling

1. **Supervisor not found**

   - No chat_id in database → Error message
   - Card not sent
   - Leave request still created

2. **Database errors**

   - Leave request creation fails → Fallback to in-memory
   - Status update fails → Logs error, continues

3. **Google Chat API errors**
   - Card send fails → Logged
   - Notification fails → Logged
   - Retry logic not implemented (future enhancement)

## Example Interaction

**Employee**:

```
I need annual leave from 2025-01-15 to 2025-01-20 for vacation
```

**Mira**:

```
Your leave request has been submitted. I'm checking your calendar for conflicts...

✅ No conflicts found. Your request is pending supervisor approval.
Request ID: req_87654321
```

**Supervisor receives card**:

```
Leave Request Approval
Request ID: req_87654321

Employee: John Doe (john@example.com)
Leave Type: Annual
Start Date: 2025-01-15
End Date: 2025-01-20
Reason: Vacation

[✅ Approve] [❌ Decline]
```

**Supervisor clicks "Approve"**

**Employee receives notification**:

```
Your leave request (req_87654321) has been approved
```

**Supervisor receives confirmation**:

```
Leave request req_87654321 has been approved and employee has been notified.
```

## Testing the Workflow

See `TESTING_GUIDE.md` for detailed testing instructions.
