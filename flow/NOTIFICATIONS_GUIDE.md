# Notification System Guide

## Overview
The BUFIA system now has a comprehensive notification system that automatically notifies users and admins about all activities related to machine rentals, rice mill appointments, and irrigation requests.

## How It Works

### Automatic Notifications
The system uses Django signals to automatically send notifications when:

1. **Machine Rentals**
   - User submits a rental request → User gets confirmation, Admins get notification
   - Admin approves rental → User gets approval notification
   - Admin rejects rental → User gets rejection notification
   - Rental is completed → User gets completion notification
   - Rental is cancelled → User gets cancellation notification

2. **Rice Mill Appointments**
   - User creates appointment → User gets confirmation, Admins get notification
   - Admin approves appointment → User gets approval notification
   - Admin rejects appointment → User gets rejection notification
   - Appointment is completed → User gets completion notification
   - Appointment is cancelled → User gets cancellation notification

3. **Irrigation Requests**
   - Farmer submits request → Farmer gets confirmation, Admins and Water Tenders get notification
   - Admin/Water Tender approves → Farmer gets approval notification
   - Admin/Water Tender rejects → Farmer gets rejection notification (with reason if provided)
   - Request is completed → Farmer gets completion notification
   - Request is cancelled → Farmer gets cancellation notification

### Notification Types

#### For Users/Farmers:
- `rental_submitted` - Rental request submitted
- `rental_approved` - Rental request approved
- `rental_rejected` - Rental request rejected
- `rental_completed` - Rental completed
- `rental_cancelled` - Rental cancelled
- `appointment_submitted` - Rice mill appointment submitted
- `appointment_approved` - Rice mill appointment approved
- `appointment_rejected` - Rice mill appointment rejected
- `appointment_completed` - Rice mill appointment completed
- `appointment_cancelled` - Rice mill appointment cancelled
- `irrigation_submitted` - Irrigation request submitted
- `irrigation_approved` - Irrigation request approved
- `irrigation_rejected` - Irrigation request rejected
- `irrigation_completed` - Irrigation request completed
- `irrigation_cancelled` - Irrigation request cancelled

#### For Admins:
- `rental_new_request` - New rental request from user
- `appointment_new_request` - New rice mill appointment from user
- `irrigation_new_request` - New irrigation request from farmer

## Admin Interface Features

### Bulk Actions
Admins can now perform bulk actions from the Django admin interface:

1. **Machine Rentals Admin**
   - Select multiple rentals
   - Choose action: "Approve selected rentals", "Reject selected rentals", or "Mark as completed"
   - All affected users will receive notifications automatically

2. **Rice Mill Appointments Admin**
   - Select multiple appointments
   - Choose action: "Approve selected appointments", "Reject selected appointments", or "Mark as completed"
   - All affected users will receive notifications automatically

3. **Irrigation Requests Admin**
   - Select multiple requests
   - Choose action: "Approve selected irrigation requests", "Reject selected irrigation requests", or "Mark as completed"
   - All affected farmers will receive notifications automatically

## Viewing Notifications

Users can view their notifications by:
1. Clicking the bell icon in the navigation bar
2. Red dot indicator shows unread notifications
3. Dropdown shows recent notifications
4. Click "View All Notifications" to see complete history

## Technical Details

### Signal Files
- `machines/signals.py` - Handles rental and rice mill appointment notifications
- `irrigation/signals.py` - Handles irrigation request notifications

### How Signals Work
1. **Pre-save signal** - Captures the old status before saving
2. **Post-save signal** - Compares old and new status, sends notifications if changed
3. Notifications are created in the `UserNotification` model
4. Users see notifications in real-time through the notification dropdown

### Testing
Run the test script to verify notifications are working:
```bash
python manage.py shell < test_notifications.py
```

## Troubleshooting

### Notifications Not Appearing
1. Check if signals are registered in `apps.py` files
2. Verify `INSTALLED_APPS` includes the apps with `.apps.ConfigName` format
3. Check Django logs for any signal errors
4. Ensure the status is actually changing (signals only fire on status change)

### Bulk Actions Not Working
1. Make sure you're using the admin interface bulk actions (not direct database updates)
2. Bulk actions iterate through each item and call `.save()` to trigger signals
3. Check admin logs for any errors

## Future Enhancements
- Email notifications for critical updates
- SMS notifications for urgent requests
- Push notifications for mobile app
- Notification preferences per user
- Notification grouping and summarization
