# Quick Start: Notification System

## For Admins

### Approving Single Items

1. Go to Django Admin: `/admin`
2. Click on:
   - **Rentals** (for machine rentals)
   - **Rice Mill Appointments** (for rice mill bookings)
   - **Water Irrigation Requests** (for irrigation requests)
3. Click on a pending item
4. Change **Status** to "Approved"
5. Click **Save**
6. ✅ User automatically receives notification!

### Bulk Approvals (Multiple Items at Once)

1. Go to Django Admin: `/admin`
2. Navigate to the relevant section
3. **Select** multiple items using checkboxes
4. Choose action from dropdown:
   - "Approve selected rentals"
   - "Approve selected appointments"
   - "Approve selected irrigation requests"
5. Click **Go**
6. ✅ All selected users automatically receive notifications!

### Other Bulk Actions Available

- **Reject** selected items
- **Mark as completed** selected items

All actions automatically send notifications to affected users.

## For Users

### Viewing Notifications

1. Look for the **bell icon (🔔)** in the navigation bar
2. **Red dot** = You have unread notifications
3. Click the bell icon to see recent notifications
4. Click **"View All Notifications"** for complete history

### What You'll Be Notified About

- ✅ Rental request submitted
- ✅ Rental request approved/rejected
- ✅ Rental completed
- ✅ Rice mill appointment submitted
- ✅ Rice mill appointment approved/rejected
- ✅ Rice mill appointment completed
- ✅ Irrigation request submitted
- ✅ Irrigation request approved/rejected
- ✅ Irrigation request completed

## Testing the System

### Quick Test (5 minutes)

1. **As User**: Create a rental request
2. **Check**: User should see "Request submitted" notification
3. **As Admin**: Approve the rental in Django admin
4. **As User**: Check notifications - should see "Request approved!" notification

### Verify It's Working

- [ ] User sees notification after creating request
- [ ] Admin sees notification about new request
- [ ] User sees notification after admin approves
- [ ] Red dot appears on bell icon for unread notifications
- [ ] Notifications show relevant details (dates, machine names, etc.)

## Troubleshooting

### "I approved something but user didn't get notification"

**Solution**: Make sure you clicked **Save** after changing the status. The notification is sent when you save the item.

### "Bulk actions aren't working"

**Solution**: 
1. Select items using checkboxes
2. Choose action from the dropdown at the top
3. Click "Go" button
4. Do NOT use the "Delete" button

### "Notifications not showing up"

**Solution**:
1. Refresh the page
2. Check if you're logged in as the correct user
3. Restart Django server: `python manage.py runserver`

## Files Modified

If you need to customize notifications:

- `machines/signals.py` - Machine rental & rice mill notifications
- `irrigation/signals.py` - Irrigation request notifications
- `machines/admin.py` - Admin bulk actions for machines
- `irrigation/admin.py` - Admin bulk actions for irrigation

## Support

For detailed information, see:
- `NOTIFICATIONS_GUIDE.md` - Complete guide
- `NOTIFICATION_FLOW.md` - System architecture
- `demo_notifications.md` - Step-by-step testing guide
- `NOTIFICATION_IMPLEMENTATION_SUMMARY.md` - Technical details

## Quick Commands

```bash
# Check system for errors
python manage.py check

# Test notifications
python manage.py shell < test_notifications.py

# View recent notifications in database
python manage.py shell
>>> from notifications.models import UserNotification
>>> UserNotification.objects.all().order_by('-timestamp')[:10]
```

## Summary

✅ **Automatic notifications** for all approvals, rejections, and completions
✅ **Bulk actions** available in Django admin
✅ **Real-time display** in user interface
✅ **Works for**: Rentals, Rice Mill Appointments, Irrigation Requests
✅ **No manual work** required - signals handle everything automatically

---

**That's it!** The notification system is now fully operational. Just approve/reject items as usual, and users will automatically receive notifications.
