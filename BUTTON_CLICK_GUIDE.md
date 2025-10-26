# Troubleshooting Button Clicks in Google Chat Cards

## Current Button Configuration

The buttons are configured correctly with:

- `actionMethodName`: APPROVE_LEAVE or DECLINE_LEAVE
- `parameters`: request_id and employee_email
- Proper `onClick` structure

## What Happens When You Click?

When you click "Approve" or "Decline" button in Google Chat:

1. **If Interactive Cards are NOT enabled**: Button clicks don't send webhook events
2. **If Interactive Cards ARE enabled**: Google Chat sends a webhook event to `/chat/webhook`

## How to Check if Interactive Cards Work

### Option 1: Watch Server Logs

When you click a button, look for:

```
🔔 Incoming webhook event: {...}
🎯 Card button action detected!
   Action method: APPROVE_LEAVE
   Parameters: [...]
```

If you don't see this, the button clicks aren't being sent to your webhook.

### Option 2: Enable Debug Logging

The current code now logs:

- All incoming webhook events
- Whether they're button actions
- Action method names
- Parameters

## Common Issues

### Issue 1: No Webhook Events Received

**Symptom**: You click the button but nothing happens, no webhook event in logs

**Cause**: Google Chat interactive cards are not enabled or configured

**Solution**:

1. Go to Google Cloud Console
2. Navigate to your Chat API configuration
3. Enable "Interactive Cards"
4. Make sure webhook URL is set to: `https://your-server.com/chat/webhook`

### Issue 2: Events Received But Not Processed

**Symptom**: Webhook events are logged but action is not processed

**Cause**: Event structure doesn't match expected format

**Solution**: Check the logged event structure and adjust parsing

### Issue 3: Buttons Show But Don't Respond

**Symptom**: Buttons appear in the card but don't trigger any action

**Cause**: Bot doesn't have permission to receive interactive events

**Solution**: Check Google Chat app permissions and ensure interactive events are enabled

## Testing Steps

1. **Send a leave request** - This creates the approval card
2. **Check server logs** - Verify card was sent successfully
3. **Click the button** - Watch for webhook event
4. **Check logs again** - Verify action was processed

## Expected Webhook Event Format

When a button is clicked, you should see:

```json
{
  "type": "CARD_CLICKED",
  "action": {
    "actionMethodName": "APPROVE_LEAVE",
    "parameters": [
      { "key": "request_id", "value": "req_123" },
      { "key": "employee_email", "value": "emp@example.com" }
    ]
  },
  "message": {
    "name": "spaces/.../messages/..."
  },
  "user": {
    "email": "supervisor@example.com"
  }
}
```

## Current Server Log Output

With the new logging, you should see:

```
🔔 Incoming webhook event: {...}
🔍 Checking for button action: action_response keys = {...}
🎯 Card button action detected!
   Action method: APPROVE_LEAVE
   Parameters: [{'key': 'request_id', 'value': 'req_123'}]
```

If you see:

```
ℹ️  Not a button action - checking other event types...
```

Then the button click events are not being sent to your webhook.

## Next Steps

1. Click a button and check server logs
2. Copy the webhook event output
3. Share what you see in the logs
4. We can then adjust the parsing accordingly

## Alternative: Use Message-Based Approach

If interactive cards don't work, we can:

- Send cards that instruct supervisor to reply with "APPROVE" or "DECLINE"
- Parse the text message in the webhook
- Process the action based on message text

This is more reliable but less user-friendly than interactive buttons.
