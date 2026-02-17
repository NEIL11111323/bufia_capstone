# Notification System Demo

## How to Test the Notification System

### Prerequisites
1. Django server running
2. At least one regular user account
3. At least one admin account

### Test Scenario 1: Machine Rental Approval

#### Step 1: User Creates Rental Request
1. Log in as a regular user
2. Go to Machines page
3. Click "Rent" on any available machine
4. Fill in the rental form (dates, purpose, etc.)
5. Submit the form
6. **Expected**: User sees confirmation message
7. **Check Notifications**: User should see notification "Your rental request has been submitted"

#### Step 2: Admin Approves Rental
1. Log out and log in as admin
2. Go to Django Admin (/admin)
3. Click on "Rentals"
4. Find the pending rental
5. Click on it
6. Change status from "Pending" to "Approved"
7. Click "Save"
8. **Expected**: Admin sees success message

#### Step 3: User Receives Approval Notification
1. Log out and log in as the regular user
2. Click the bell icon (🔔) in the navigation bar
3. **Expected**: User sees notification "Your rental request for [Machine Name] has been approved!"
4. Red dot indicator should appear if notification is unread

### Test Scenario 2: Rice Mill Appointment Approval

#### Step 1: User Creates Appointment
1. Log in as a regular user
2. Go to Machines page
3. Find a Rice Mill machine
4. Click "Schedule Appointment"
5. Fill in appointment details (date, time slot, quantity)
6. Submit the form
7. **Expected**: User sees confirmation with reference number
8. **Check Notifications**: User should see notification about submission

#### Step 2: Admin Approves Appointment
1. Log in as admin
2. Go to Django Admin (/admin)
3. Click on "Rice Mill Appointments"
4. Find the pending appointment
5. Select it using checkbox
6. Choose action: "Approve selected appointments"
7. Click "Go"
8. **Expected**: Admin sees "[X] appointment(s) approved successfully"

#### Step 3: User Receives Approval Notification
1. Log in as the regular user
2. Click the bell icon (🔔)
3. **Expected**: User sees notification "Your rice mill appointment has been approved!"
4. Notification includes reference number

### Test Scenario 3: Irrigation Request Approval

#### Step 1: Farmer Creates Irrigation Request
1. Log in as a verified farmer
2. Go to Irrigation Requests page
3. Click "Create New Request"
4. Fill in request details (date, area, crop type, etc.)
5. Submit the form
6. **Expected**: Farmer sees confirmation message
7. **Check Notifications**: Farmer should see notification about submission

#### Step 2: Admin/Water Tender Approves Request
1. Log in as admin or water tender
2. Go to Django Admin (/admin)
3. Click on "Water Irrigation Requests"
4. Find the pending request
5. Select multiple requests using checkboxes
6. Choose action: "Approve selected irrigation requests"
7. Click "Go"
8. **Expected**: Admin sees "[X] irrigation request(s) approved successfully"

#### Step 3: Farmer Receives Approval Notification
1. Log in as the farmer
2. Click the bell icon (🔔)
3. **Expected**: Farmer sees notification "Your irrigation request has been approved!"
4. Notification includes sector and date information

### Test Scenario 4: Bulk Approvals

#### Testing Bulk Actions
1. Log in as admin
2. Go to Django Admin
3. Navigate to Rentals/Appointments/Irrigation Requests
4. Select multiple pending items (3-5 items)
5. Choose bulk action (e.g., "Approve selected rentals")
6. Click "Go"
7. **Expected**: All selected items are approved
8. **Expected**: All affected users receive notifications

#### Verify Notifications
1. Log in as each affected user
2. Check bell icon
3. **Expected**: Each user sees their specific approval notification
4. Notifications should be personalized with machine/appointment/request details

### Test Scenario 5: Rejection Notifications

#### Test Rejection Flow
1. Create a new rental/appointment/irrigation request as user
2. Log in as admin
3. Go to Django Admin
4. Find the pending item
5. Change status to "Rejected"
6. Save
7. Log in as the user
8. Check notifications
9. **Expected**: User sees rejection notification

### Test Scenario 6: Completion Notifications

#### Test Completion Flow
1. Find an approved rental/appointment/irrigation request
2. Log in as admin
3. Go to Django Admin
4. Change status to "Completed"
5. Save
6. Log in as the user
7. Check notifications
8. **Expected**: User sees completion notification with thank you message

## Verification Checklist

- [ ] User receives notification when creating rental request
- [ ] Admin receives notification about new rental request
- [ ] User receives notification when rental is approved
- [ ] User receives notification when rental is rejected
- [ ] User receives notification when rental is completed
- [ ] User receives notification when creating rice mill appointment
- [ ] Admin receives notification about new appointment
- [ ] User receives notification when appointment is approved
- [ ] User receives notification when appointment is rejected
- [ ] User receives notification when appointment is completed
- [ ] Farmer receives notification when creating irrigation request
- [ ] Admin and water tenders receive notification about new irrigation request
- [ ] Farmer receives notification when irrigation request is approved
- [ ] Farmer receives notification when irrigation request is rejected
- [ ] Farmer receives notification when irrigation request is completed
- [ ] Bulk approvals send notifications to all affected users
- [ ] Red dot indicator appears for unread notifications
- [ ] Notification dropdown shows recent notifications
- [ ] Notifications include relevant details (dates, machine names, etc.)

## Troubleshooting

### Notifications Not Appearing
1. Check browser console for JavaScript errors
2. Refresh the page
3. Check if signals are properly registered (restart Django server)
4. Verify notification was created in database:
   ```python
   python manage.py shell
   >>> from notifications.models import UserNotification
   >>> UserNotification.objects.all().order_by('-timestamp')[:10]
   ```

### Admin Actions Not Working
1. Make sure you're using the bulk actions dropdown (not direct database updates)
2. Check Django admin logs for errors
3. Verify you have proper permissions

### Signal Errors
1. Check Django server logs for signal errors
2. Verify apps.py files have `ready()` method
3. Ensure signals.py files are in the correct location
4. Restart Django server after making changes

## Success Indicators

✅ Users receive notifications immediately after admin actions
✅ Notification bell shows red dot for unread notifications
✅ Notification messages are clear and include relevant details
✅ Bulk actions work and send notifications to all affected users
✅ Both users and admins receive appropriate notifications
✅ Water tenders receive notifications for their sector's irrigation requests
