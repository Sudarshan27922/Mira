# Google Calendar Setup Guide for Mira

This guide shows you how to configure Google Calendar access for Mira to check your calendar for meetings and conflicts.

## Setup Method 1: Individual Calendar Sharing (Recommended for Testing)

### Step 1: Find Your Service Account Email

Your service account email is:

```
mira-service@mira-473511.iam.gserviceaccount.com
```

### Step 2: Share Your Calendar

1. **Open Google Calendar**: Go to [calendar.google.com](https://calendar.google.com)

2. **Open Settings**:

   - Click the gear icon ⚙️ (top right)
   - Select "Settings"

3. **Go to Calendar Settings**:

   - In the left sidebar, find your calendar under "Settings for my calendars"
   - Click on your calendar name

4. **Share with Specific People**:

   - Scroll down to "Share with specific people"
   - Click "+ Add people"

5. **Add Service Account**:

   - Enter: `mira-service@mira-473511.iam.gserviceaccount.com`
   - Set permission: **"See all event details"**
   - Click "Send"

6. **Verify**:
   - You should see the service account email listed under "People with access"
   - Permission should be "See all event details"

### Step 3: Test Calendar Access

After sharing your calendar, test with these queries:

```
"do i have meetings tomorrow"
"what's my calendar look like next week"
"am i free on monday"
```

The system should now be able to see your calendar events.

---

## Setup Method 2: Domain-Wide Delegation (For Organizations)

If you have Google Workspace admin access and want organization-wide access:

### Step 1: Enable Domain-Wide Delegation in Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `mira-473511`
3. Navigate to **APIs & Services** → **Credentials**
4. Find your service account: `mira-service@mira-473511.iam.gserviceaccount.com`
5. Click on it
6. Copy the **Client ID**: `108696430212333379245`

### Step 2: Configure in Google Workspace Admin

1. Go to [Admin Console](https://admin.google.com/)
2. Navigate to **Security** → **API Controls**
3. Find **Domain-wide delegation** section
4. Click **Add new**
5. Enter:
   - **Client ID**: `108696430212333379245`
   - **OAuth Scopes**:
     ```
     https://www.googleapis.com/auth/calendar.readonly,
     https://www.googleapis.com/auth/chat.bot,
     https://www.googleapis.com/auth/chat.messages,
     https://www.googleapis.com/auth/chat.spaces
     ```
6. Click **Authorize**

### Step 3: Verify

After setup, Mira can access calendars for any user in your Google Workspace domain without individual sharing.

---

## Troubleshooting

### Issue: "Calendar service not initialized"

**Solution**: Restart your FastAPI server after enabling Google Calendar API

### Issue: "Unable to retrieve calendar" or "Calendar not shared"

**Solution**:

- Verify calendar is shared with `mira-service@mira-473511.iam.gserviceaccount.com`
- Check permission is set to "See all event details" (not "Make changes to events")
- Wait a few minutes after sharing for permissions to propagate

### Issue: "No events found" when you know you have meetings

**Possible causes**:

1. **All-day events**: Currently filtered out (will be fixed)
2. **Declined meetings**: Filtered out
3. **Date format**: Ensure dates are in YYYY-MM-DD format
4. **Timezone**: Events are in UTC, may need timezone adjustment

### Issue: Wrong date range returned

**Solution**: The system queries from `start_date 00:00:00 UTC` to `end_date 23:59:59 UTC`. For better accuracy:

- Use specific dates (YYYY-MM-DD format)
- Account for timezone differences

### Issue: Permissions error

**Solution**:

- Ensure Google Calendar API is enabled in Google Cloud Console
- Check service account has proper scopes
- Verify domain-wide delegation is properly configured (if using that method)

---

## Environment Configuration

Make sure your `.env` file has:

```bash
# Calendar Configuration
USE_DOMAIN_DELEGATION=true  # Use domain-wide delegation
# OR
USE_DOMAIN_DELEGATION=false  # Use individual calendar sharing

# Service Account Configuration
SERVICE_ACCOUNT_KEY_FILE=./server/service-account-key.json
```

---

## Testing Calendar Access

After setup, you can test with these queries:

### General Calendar Queries

```
"do i have meetings tomorrow"
"what's my schedule for next week"
"am i free on december 25"
```

### Leave Request (Automatic Conflict Check)

```
"i want leave next monday"
Agent will automatically check for meetings and show conflicts
```

### Direct Calendar Tool

The HR Agent can now use `query_user_calendar` tool directly for any calendar inquiry.

---

## Current Limitations

1. **All-day events**: Currently filtered out (not included in results)
2. **Declined meetings**: Automatically excluded
3. **Timezone**: All times shown in UTC (may need conversion)
4. **Recurring events**: Treated as single events

These will be improved in future updates.

---

## Need Help?

If you're still having issues:

1. Check server logs for detailed error messages
2. Verify calendar sharing with service account email
3. Ensure Google Calendar API is enabled
4. Restart server after any configuration changes
