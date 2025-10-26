# Supervisor Leave Approval Implementation

## Overview

This implementation provides an end-to-end leave approval workflow using Google Chat cards. When an employee requests leave, their supervisor receives an interactive card with approve/decline buttons.

## Features

1. **Database Integration**: Leave requests are stored in the `leave_requests` table
2. **Supervisor Cards**: Interactive cards sent to supervisor's Google Chat space
3. **Button Actions**: Approve/Decline buttons trigger webhook handlers
4. **Notifications**: Both supervisor and employee receive status updates
5. **Real-time Updates**: Cards update to show decision status

## Database Schema

### New Fields

**employee table**:

- `chat_id` (VARCHAR): Google Chat space ID for each employee

### New Table

**leave_requests table**:

- `id` (SERIAL PRIMARY KEY)
- `request_id` (VARCHAR UNIQUE): Unique identifier for the request
- `employee_email` (VARCHAR): Employee who requested leave
- `supervisor_email` (VARCHAR): Supervisor who needs to approve
- `leave_type` (VARCHAR): Type of leave (Annual, Sick, etc.)
- `start_date` (DATE): Leave start date
- `end_date` (DATE): Leave end date
- `reason` (TEXT): Reason for leave
- `employee_space` (VARCHAR): Employee's Google Chat space ID
- `status` (VARCHAR): PENDING, APPROVED, DECLINED, or CANCELLED
- `created_at` (TIMESTAMP): When request was created
- `updated_at` (TIMESTAMP): Last update time
- `approved_at` (TIMESTAMP): When approved/declined
- `decision_note` (TEXT): Note from supervisor

## Installation

### 1. Run Database Migration

```bash
psql -U your_user -d your_database -f database_migration.sql
```

### 2. Update Employee Records

Update each employee record with their Google Chat space ID:

```sql
UPDATE public.employee
SET chat_id = 'spaces/<YOUR_SPACE_ID>'
WHERE emp_email = 'employee@example.com';
```

### 3. Environment Variables

Ensure these are set in your `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost/dbname
PORT=3005
SERVICE_ACCOUNT_KEY_FILE=./service-account-key.json
```

## Workflow

### Employee Request Flow

1. Employee sends leave request message to Google Chat
2. Mira agent collects details (dates, type, reason)
3. System checks for calendar conflicts
4. Leave request is saved to database with status `PENDING`
5. Supervisor's chat_id is retrieved from database
6. Approval card is sent to supervisor's space

### Supervisor Approval Flow

1. Supervisor receives interactive card in their chat space
2. Card shows:
   - Employee name and email
   - Leave type
   - Start date and end date
   - Reason
   - Approve/Decline buttons
3. Supervisor clicks Approve or Decline
4. Webhook handler processes the action
5. Database is updated with new status
6. Card in supervisor space is updated to show decision
7. Employee is notified in their space
8. Supervisor receives confirmation message

## API Endpoints

### POST `/chat/send-approval-card`

Sends an approval card to supervisor.

Request:

```json
{
  "requestId": "req_123456",
  "employeeEmail": "employee@example.com",
  "employeeName": "John Doe",
  "supervisorEmail": "supervisor@example.com",
  "supervisorSpace": "spaces/AAAAxxxxxxx",
  "leaveType": "Annual",
  "startDate": "2025-01-15",
  "endDate": "2025-01-20",
  "reason": "Family vacation"
}
```

## Database Functions

### Create Leave Request

```python
from agents.utils import db_util

result = db_util.create_leave_request({
    "request_id": "req_123",
    "employee_email": "emp@example.com",
    "supervisor_email": "supervisor@example.com",
    "leave_type": "Annual",
    "start_date": "2025-01-15",
    "end_date": "2025-01-20",
    "reason": "Vacation",
    "employee_space": "spaces/AAAAxxxxxxx",
    "status": "PENDING"
})
```

### Get Leave Request

```python
leave_request = db_util.get_leave_request("req_123")
```

### Update Leave Request Status

```python
db_util.update_leave_request_status(
    request_id="req_123",
    new_status="APPROVED",
    decision_note="Approved by supervisor"
)
```

## HR Agent Integration

The leave approval workflow is integrated into the HR agent tools:

### record_leave_request Tool

Saves leave requests to the database.

### send_supervisor_approval Tool

Sends approval cards to supervisors via Google Chat.

### leave_process_workflow Tool

Orchestrates the complete workflow:

1. Validates required fields
2. Records leave request in database
3. Checks for calendar conflicts
4. Sends approval card to supervisor

## Webhook Handler

The webhook handler at `/chat/webhook` now processes card button actions:

- Detects action events (APPROVE_LEAVE, DECLINE_LEAVE)
- Extracts parameters (request_id, employee_email)
- Updates database with decision
- Updates card in supervisor space
- Notifies employee
- Sends confirmation to supervisor

## Testing

### Test Leave Request

Send a message to Google Chat:

```
I need to request leave from 2025-01-15 to 2025-01-20 for Annual leave. Reason: Vacation.
```

### Check Database

```sql
SELECT * FROM public.leave_requests ORDER BY created_at DESC;
```

### Monitor Logs

Check server logs for:

- Leave request creation
- Supervisor card sending
- Button action processing
- Database updates
- Notifications sent

## Troubleshooting

### Issue: Supervisor never receives card

**Solutions**:

1. Verify supervisor has `chat_id` set in database
2. Check supervisor email matches manager_email
3. Ensure supervisor is in Google Chat space
4. Check server logs for errors

### Issue: Buttons don't work

**Solutions**:

1. Verify Google Chat bot has proper permissions
2. Check webhook URL is configured correctly
3. Ensure action event is being received (check logs)
4. Verify request_id exists in database

### Issue: Employee not notified

**Solutions**:

1. Check employee_space is saved with request
2. Verify employee's chat_id is set in database
3. Check notification is being sent (check logs)

## Files Modified

- `agents/utils/user_context.py`: Added chat_id retrieval and `get_supervisor_info()`
- `agents/utils/db_util.py`: New file with leave request CRUD operations
- `server/main.py`: Added approval card function, button handler, and endpoint
- `agents/mira/sub_agents/hr/tools.py`: Implemented database operations
- `database_migration.sql`: Database schema changes

## Future Enhancements

- Add bulk leave request approval
- Implement auto-approval for certain leave types
- Add approval history and audit logging
- Support multiple supervisor levels
- Add email notifications as backup
- Implement leave balance tracking
