# Rental Request Notifications System - Complete Guide

## Overview
The rental request notifications system automatically sends notifications to users and admins for all rental-related events. This system uses Django signals to trigger notifications whenever rental status changes occur.

## Four Key Notification Scenarios

### 1. ✅ New Rental Request Submitted
**Trigger:** When a user creates a new rental request
**Recipients:** 
- User who submitted the request
- All active admin users (is_staff=True)

**User Notification:**
```
Type: rental_submitted
Message: "Your rental request for [Machine Name] from [Start Date] to [End Date] has been submitted and is pending approval."
```

**Admin Notification:**
```
Type: rental_new_request
Message: "New rental request from [User Name] for [Machine Name] from [Start Date] to [End Date]."
```

**Implementation:** `machines/signals.py` - `notify_rental_status_change()` signal handler

---

### 2. ✅ Approved Rental Request
**Trigger:** When admin changes rental status from 'pending' to 'approved'
**Recipients:** User who submitted the rental request

**Notification:**
```
Type: rental_approved
Message: "Your rental request for [Machine Name] from [Start Date] to [End Date] has been approved!"
```

**Side Effects:**
- Machine status may be updated to 'rented' if currently available
- User can now proceed with the rental

**Implementation:** `machines/signals.py` - `notify_rental_status_change()` signal handler

---

### 3. ✅ Declined Rental Request
**Trigger:** When admin changes rental status from 'pending' to 'rejected'
**Recipients:** User who submitted the rental request

**Notification:**
```
Type: rental_rejected
Message: "Your rental request for [Machine Name] from [Start Date] to [End Date] has been rejected."
```

**Side Effects:**
- Machine status may be updated back to 'available' if no other active rentals exist
- User can submit a new rental request

**Implementation:** `machines/signals.py` - `notify_rental_status_change()` signal handler

---

### 4. ✅ Rental Schedule Conflict Detected
**Trigger:** When a user attempts to book a machine for dates that overlap with existing rentals
**Recipients:** 
- User who attempted the booking (primary notification)
- Other verified members in the same sector (broadcast notification)

**User Notification:**
```
Type: rental_conflict
Message: "[Machine Name] is already rented from [Start Date] to [End Date]. Please rent this on another day."
```

**Broadcast Notification (to other members):**
```
Type: rental_conflict_broadcast
Message: "[Machine Name] is already rented from [Start Date] to [End Date]. Please rent this on another day."
```

**Implementation:** `machines/views.py` - `rental_create()` view function

**Conflict Detection Logic:**
- Uses overlap formula: `(start <= existing_end) AND (end >= existing_start)`
- Checks both 'approved' and 'pending' rentals
- Prevents same-day conflicts
- Validates against maintenance schedules

---

## Technical Implementation

### Signal Handlers (`machines/signals.py`)

#### Pre-Save Signal
```python
@receiver(pre_save, sender=Rental)
def track_rental_status_change(sender, instance, **kwargs):
    """Track status changes before saving"""
    if instance.pk:
        old_instance = Rental.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
```

#### Post-Save Signal
```python
@receiver(post_save, sender=Rental)
def notify_rental_status_change(sender, instance, created, **kwargs):
    """Send notifications based on rental status"""
    if created:
        # Scenario 1: New rental submitted
        # Notify user and all admins
    else:
        # Scenarios 2 & 3: Status changed
        # Check old_status vs new status
        # Send appropriate notification
```

### Form Validation (`machines/forms.py`)

The `RentalForm.clean()` method performs comprehensive validation:

1. **Date Validation**
   - End date must be after or equal to start date
   - Start date cannot be in the past
   - Maximum rental period: 30 days
   - Minimum advance booking: 1 day

2. **Availability Check**
   ```python
   is_available, conflicts = Rental.check_availability(
       machine=machine,
       start_date=start_date,
       end_date=end_date,
       exclude_rental_id=exclude_id
   )
   ```

3. **Maintenance Check**
   - Verifies machine is not scheduled for maintenance during rental period

### Conflict Detection (`machines/models.py`)

```python
@classmethod
def check_availability(cls, machine, start_date, end_date, exclude_rental_id=None):
    """
    Check if a machine is available for the given date range.
    Uses overlap formula: (start < existing_end) AND (end > existing_start)
    """
    overlapping = cls.objects.filter(
        machine=machine,
        status__in=['approved', 'pending'],
        start_date__lte=end_date,  # <= to detect same-day conflicts
        end_date__gte=start_date   # >= to detect same-day conflicts
    )
    
    if exclude_rental_id:
        overlapping = overlapping.exclude(id=exclude_rental_id)
    
    is_available = not overlapping.exists()
    return is_available, overlapping
```

---

## Notification Model (`notifications/models.py`)

```python
class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=100)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    related_object_id = models.IntegerField(null=True, blank=True)
    action_url = models.CharField(max_length=255, null=True, blank=True)
```

### Notification Types
- `rental_submitted` - User submitted a new rental request
- `rental_new_request` - Admin notification for new request
- `rental_approved` - Rental request was approved
- `rental_rejected` - Rental request was rejected
- `rental_conflict` - User attempted to book conflicting dates
- `rental_conflict_broadcast` - Broadcast to other members about conflict
- `rental_completed` - Rental was marked as completed
- `rental_cancelled` - Rental was cancelled

---

## User Flow

### Successful Rental Request
```
1. User fills out rental form
2. Form validates dates and availability
3. Rental created with status='pending'
4. Signal triggers notifications:
   - User receives "rental_submitted" notification
   - All admins receive "rental_new_request" notification
5. User redirected to payment page
6. Admin reviews and approves
7. Signal triggers "rental_approved" notification to user
```

### Conflicting Rental Request
```
1. User fills out rental form
2. Form validates dates
3. Availability check detects conflict
4. Form validation fails with error message
5. View creates "rental_conflict" notification for user
6. View broadcasts "rental_conflict_broadcast" to other members
7. User sees error message and notification
8. User can choose different dates
```

---

## Testing the System

### Test Scenario 1: New Rental Request
```python
# Create a rental request
rental = Rental.objects.create(
    machine=machine,
    user=user,
    start_date=date(2025, 12, 10),
    end_date=date(2025, 12, 15),
    status='pending'
)

# Check notifications
user_notif = UserNotification.objects.filter(
    user=user,
    notification_type='rental_submitted'
).latest('timestamp')

admin_notifs = UserNotification.objects.filter(
    notification_type='rental_new_request'
)
```

### Test Scenario 2: Approve Rental
```python
# Approve the rental
rental.status = 'approved'
rental.save()

# Check notification
approval_notif = UserNotification.objects.filter(
    user=user,
    notification_type='rental_approved'
).latest('timestamp')
```

### Test Scenario 3: Reject Rental
```python
# Reject the rental
rental.status = 'rejected'
rental.save()

# Check notification
rejection_notif = UserNotification.objects.filter(
    user=user,
    notification_type='rental_rejected'
).latest('timestamp')
```

### Test Scenario 4: Conflict Detection
```python
# Try to create overlapping rental via form
form = RentalForm(data={
    'machine': machine.id,
    'start_date': date(2025, 12, 12),  # Overlaps with existing
    'end_date': date(2025, 12, 17),
})

# Form should be invalid
assert not form.is_valid()

# Check for conflict notification
conflict_notif = UserNotification.objects.filter(
    user=user,
    notification_type='rental_conflict'
).latest('timestamp')
```

---

## Notification Viewing

Users can view their notifications at:
- **URL:** `/notifications/all/`
- **View:** `notifications.views.all_notifications`
- **Template:** `notifications/templates/notifications/all_notifications.html`

### Notification Detail View
- **URL:** `/notifications/<id>/`
- **View:** `notifications.views.notification_detail`
- **Template:** `notifications/templates/notifications/notification_detail.html`

### Features
- Mark as read/unread
- Delete notifications
- View related rental details
- Direct links to rental pages

---

## Admin Dashboard Integration

Admins can manage rental requests from:
- **URL:** `/machines/rentals/`
- **View:** `machines.views.rental_list`
- **Template:** `machines/templates/machines/rental_list.html`

### Admin Actions
- View all rental requests
- Filter by status (pending, approved, rejected)
- Bulk approve/reject rentals
- View payment verification status
- Check for date conflicts

---

## Best Practices

### For Users
1. Check machine availability calendar before booking
2. Book at least 1 day in advance
3. Provide accurate dates and details
4. Complete payment promptly after booking
5. Check notifications regularly for updates

### For Admins
1. Review rental requests promptly
2. Verify payment before approval
3. Check for date conflicts before approving
4. Communicate rejection reasons to users
5. Monitor machine maintenance schedules

---

## Troubleshooting

### Notifications Not Appearing
1. Check if signals are registered in `machines/apps.py`:
   ```python
   def ready(self):
       import machines.signals
   ```

2. Verify notification model is working:
   ```python
   python manage.py shell
   >>> from notifications.models import UserNotification
   >>> UserNotification.objects.all()
   ```

3. Check signal handlers are executing:
   - Add print statements in signal handlers
   - Check Django logs

### Conflict Detection Not Working
1. Verify overlap formula in `Rental.check_availability()`
2. Check rental status filters (should include 'pending' and 'approved')
3. Ensure form validation is calling `check_availability()`

### Notifications Not Sent to Admins
1. Verify admin users have `is_staff=True` and `is_active=True`
2. Check signal handler is querying admins correctly:
   ```python
   admins = User.objects.filter(is_staff=True, is_active=True)
   ```

---

## Future Enhancements

### Potential Improvements
1. **Email Notifications** - Send email alerts for critical events
2. **SMS Notifications** - Text message alerts for urgent updates
3. **Push Notifications** - Browser push notifications
4. **Notification Preferences** - Let users customize notification types
5. **Notification Grouping** - Group similar notifications
6. **Real-time Updates** - WebSocket-based live notifications
7. **Notification History** - Archive old notifications
8. **Notification Analytics** - Track notification engagement

---

## Summary

The rental request notifications system provides comprehensive coverage of all rental-related events:

✅ **New Request Submitted** - Users and admins notified immediately
✅ **Request Approved** - User receives confirmation
✅ **Request Declined** - User informed of rejection
✅ **Conflict Detected** - User and community alerted to booking conflicts

The system uses Django signals for automatic notification triggering, comprehensive form validation for conflict detection, and a flexible notification model for easy extension.

All notifications are stored in the database, viewable through the web interface, and can be marked as read or deleted by users.
