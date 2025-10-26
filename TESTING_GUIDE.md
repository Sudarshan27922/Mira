# Testing Guide for Leave Approval Implementation

## Prerequisites

1. **Database Setup**

   ```bash
   # Run the migration
   psql -U your_user -d your_database -f database_migration.sql
   ```

2. **Update Employee Records**

   ```sql
   -- Add chat_id to employees
   UPDATE public.employee
   SET chat_id = 'spaces/AAAAAAAAAAA'
   WHERE emp_email = 'employee@example.com';

   -- Add chat_id to supervisors
   UPDATE public.employee
   SET chat_id = 'spaces/BBBBBBBBBBB'
   WHERE emp_email = 'supervisor@example.com';
   ```

3. **Environment Variables**
   Ensure `.env` has:
   ```
   DATABASE_URL=postgresql://user:password@localhost/dbname
   PORT=3005
   SERVICE_ACCOUNT_KEY_FILE=./service-account-key.json
   ```

## Testing Methods

### Method 1: Unit Tests (No Database Required)

```bash
python test_leave_approval.py
```

This tests:

- ✅ Database utility functions
- ✅ Card structure validation
- ✅ Webhook event parsing
- ✅ User context retrieval

### Method 2: Integration Test (Requires Database)

#### Test Database Operations

```python
from agents.utils import db_util

# Create a leave request
result = db_util.create_leave_request({
    "request_id": "test_001",
    "employee_email": "emp@example.com",
    "supervisor_email": "sup@example.com",
    "leave_type": "Annual",
    "start_date": "2025-01-15",
    "end_date": "2025-01-20",
    "reason": "Vacation",
    "employee_space": "spaces/AAAAxxxxxxx",
    "status": "PENDING"
})
print(result)  # Should return: {'request_id': 'test_001', 'status': 'CREATED'}

# Get the request
leave = db_util.get_leave_request("test_001")
print(leave)  # Should show all details

# Update status
db_util.update_leave_request_status("test_001", "APPROVED", "Approved by manager")
```

#### Test User Context

```python
from agents.utils import user_context

# Get user context
user_info = user_context.get_user_context_from_db("employee@example.com")
print(user_info)  # Should include chat_id

# Get supervisor info
supervisor = user_context.get_supervisor_info("supervisor@example.com")
print(supervisor)  # Should include chat_id
```

### Method 3: End-to-End Test (Requires Google Chat)

1. **Start the server**

   ```bash
   cd server
   python main.py
   ```

2. **Test via Google Chat**

   - Go to your Google Chat space
   - Send message: "I need to request leave from 2025-01-15 to 2025-01-20 for Annual leave. Reason: Vacation"
   - Check server logs for:
     - Leave request creation
     - Supervisor card being sent
     - Database updates

3. **Test Card Button Interaction**
   - Supervisor receives card
   - Clicks "Approve" or "Decline"
   - Check:
     - Card updates in supervisor space
     - Employee notified in their space
     - Database status updated

## Manual Testing Checklist

### Pre-requisites

- [ ] Database migration run successfully
- [ ] At least one employee record has `chat_id` set
- [ ] At least one supervisor (manager_email) has `chat_id` set
- [ ] Employee has `manager_email` pointing to supervisor
- [ ] Server is running and accessible

### Test Flow

1. **Leave Request Creation**

   - [ ] Employee sends leave request via chat
   - [ ] Server logs show leave request created
   - [ ] Database has new entry with status PENDING
   - [ ] Employee receives confirmation message

2. **Approval Card Sending**

   - [ ] Supervisor receives approval card
   - [ ] Card shows correct employee details
   - [ ] Card shows correct leave details
   - [ ] Approve and Decline buttons are visible

3. **Button Interaction**

   - [ ] Clicking Approve updates database to APPROVED
   - [ ] Clicking Decline updates database to DECLINED
   - [ ] Card in supervisor space updates to show decision
   - [ ] Employee receives notification in their space
   - [ ] Supervisor receives confirmation message

4. **Error Handling**
   - [ ] Request not found (invalid request_id)
   - [ ] Supervisor not found (no chat_id)
   - [ ] Database connection errors
   - [ ] Google Chat API errors

## Common Issues and Solutions

### Issue: Database migration fails

**Error**: `column "chat_id" does not exist`

**Solution**: The migration script has a safety check. If you see this error, the column doesn't exist yet. Run the migration:

```bash
psql -U your_user -d your_database -f database_migration.sql
```

### Issue: Supervisor never receives card

**Possible causes**:

1. Supervisor doesn't have `chat_id` set in database
2. Employee's `manager_email` doesn't match supervisor's email
3. Google Chat API credentials not set up

**Check**:

```sql
-- Check if supervisor exists
SELECT emp_email, chat_id FROM public.employee WHERE emp_email = 'supervisor@example.com';

-- Check if employee has manager
SELECT emp_email, manager_email FROM public.employee WHERE emp_email = 'employee@example.com';
```

### Issue: Buttons don't do anything

**Possible causes**:

1. Webhook URL not configured in Google Chat
2. Bot doesn't have permission to receive actions
3. Event structure doesn't match expected format

**Solution**: Check server logs for event data when clicking button.

### Issue: Employee not notified

**Possible causes**:

1. `employee_space` not saved with request
2. Employee doesn't have `chat_id` in database

**Solution**: Verify request in database has `employee_space` field set.

## API Testing

### Test Approval Card Endpoint

```bash
curl -X POST http://localhost:3005/chat/send-approval-card \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "test_001",
    "employeeEmail": "emp@example.com",
    "employeeName": "John Doe",
    "supervisorEmail": "sup@example.com",
    "supervisorSpace": "spaces/BBBBBBBBBBB",
    "leaveType": "Annual",
    "startDate": "2025-01-15",
    "endDate": "2025-01-20",
    "reason": "Vacation"
  }'
```

Expected response:

```json
{
  "success": true,
  "messageId": "spaces/.../messages/...",
  "space": "spaces/BBBBBBBBBBB",
  "request_id": "test_001"
}
```

## Logging

Check server logs for:

### Leave Request Created

```
✅ Leave request created: test_001
```

### Card Sent

```
✅ Sent approval card to supervisor@example.com
```

### Button Clicked

```
🎯 Card button action detected
🎯 Processing APPROVE_LEAVE for request test_001
✅ Updated card in supervisor space
✅ Notified employee in space spaces/AAAAxxxxxxx
```

## Database Verification

After testing, verify in database:

```sql
-- Check leave requests
SELECT request_id, employee_email, supervisor_email, status, created_at
FROM public.leave_requests
ORDER BY created_at DESC
LIMIT 5;

-- Check updated status
SELECT request_id, status, decision_note, approved_at
FROM public.leave_requests
WHERE request_id = 'test_001';
```

## Performance Testing

For load testing:

1. Create multiple leave requests rapidly
2. Monitor database query performance
3. Check for any race conditions
4. Verify all requests get unique IDs

```python
import concurrent.futures
from agents.utils import db_util

def create_request(i):
    return db_util.create_leave_request({
        "request_id": f"test_{i:05d}",
        "employee_email": f"emp{i}@example.com",
        # ... other fields
    })

# Test with 100 concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(create_request, range(100))
```

## Success Criteria

✅ All unit tests pass
✅ Database operations work correctly
✅ Approval cards are sent successfully
✅ Button interactions update database
✅ Both parties receive notifications
✅ Error handling works gracefully
✅ No data loss in transactions
