# Operator-Admin Communication Flow Diagram

## Complete Workflow Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RENTAL WORKFLOW WITH NOTIFICATIONS                │
└─────────────────────────────────────────────────────────────────────┘

MEMBER                    ADMIN                    OPERATOR
  │                         │                          │
  │  1. Submit Rental       │                          │
  ├────────────────────────>│                          │
  │                         │                          │
  │  ← Notification         │  2. Review & Approve     │
  │    "Rental Submitted"   │                          │
  │                         │                          │
  │                         │  3. Assign Operator      │
  │                         ├─────────────────────────>│
  │                         │                          │
  │                         │  ← Notification          │
  │                         │    "Assigned to rental"  │
  │                         │                          │
  │                         │                          │  4. Update Status
  │                         │                          │     (traveling)
  │                         │<─────────────────────────┤
  │                         │                          │
  │                         │  ← Notification          │
  │                         │    "Operator traveling"  │
  │                         │                          │
  │                         │                          │  5. Update Status
  │                         │                          │     (operating)
  │                         │<─────────────────────────┤
  │                         │                          │
  │                         │  ← Notification          │
  │                         │    "Operator operating"  │
  │                         │                          │
  │                         │                          │  6. Submit Harvest
  │                         │                          │     Report
  │                         │<─────────────────────────┤
  │                         │                          │
  │                         │  ← Notification          │
  │                         │    "Harvest: X sacks"    │
  │                         │                          │
  │                         │  7. Confirm Delivery     │
  │                         │                          │
  │  ← Notification         │                          │
  │    "Rental Completed"   │                          │
  │                         │                          │
  └─────────────────────────┴──────────────────────────┘
```

## Notification Types by Role

### Admin Receives:
```
┌─────────────────────────────────────────┐
│  ADMIN NOTIFICATION DASHBOARD           │
├─────────────────────────────────────────┤
│  ✉ New rental request from [Member]    │
│  ✉ Operator status: Traveling           │
│  ✉ Operator status: Operating           │
│  ✉ Harvest reported: 100 sacks          │
│  ✉ Payment proof uploaded               │
└─────────────────────────────────────────┘
```

### Operator Receives:
```
┌─────────────────────────────────────────┐
│  OPERATOR NOTIFICATION DASHBOARD        │
├─────────────────────────────────────────┤
│  ✉ Assigned to operate [Machine]       │
│     for [Member]                        │
└─────────────────────────────────────────┘
```

### Member Receives:
```
┌─────────────────────────────────────────┐
│  MEMBER NOTIFICATION DASHBOARD          │
├─────────────────────────────────────────┤
│  ✉ Rental request submitted             │
│  ✉ Rental approved                      │
│  ✉ Payment received                     │
│  ✉ Rental in progress                   │
│  ✉ Harvest recorded                     │
│  ✉ Rental completed                     │
└─────────────────────────────────────────┘
```

## Status Synchronization

### Operator Status Flow
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  unassigned  │────>│   assigned   │────>│  traveling   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                            │                      v
                            │              ┌──────────────┐
                            │              │  operating   │
                            │              └──────────────┘
                            │                      │
                            │                      v
                            │              ┌──────────────┐
                            └─────────────>│   harvest    │
                                          │   reported   │
                                          └──────────────┘
```

### Database Fields Updated
```
operator_status              → Current status
operator_last_update_at      → Timestamp of last update
operator_reported_at         → Harvest report timestamp
operator_notes               → Operator comments
workflow_state               → Overall rental state
```

## Notification Implementation

### Helper Function
```python
def _notify_admins(message, rental_id, *, exclude_user_id=None):
    """
    Notify all active admin users about rental updates
    
    Args:
        message: Notification message
        rental_id: Related rental ID
        exclude_user_id: Optional user ID to exclude (e.g., triggering user)
    """
    admins = User.objects.filter(is_active=True, is_staff=True)
    if exclude_user_id:
        admins = admins.exclude(pk=exclude_user_id)
    
    notifications = [
        UserNotification(
            user=admin,
            notification_type='rental_update',
            message=message,
            related_object_id=rental_id,
        )
        for admin in admins
    ]
    
    if notifications:
        UserNotification.objects.bulk_create(notifications)
```

### Usage Examples

**Operator Status Update:**
```python
_notify_admins(
    f'Operator update for {rental.machine.name}: {rental.get_operator_status_display()}.',
    rental.id,
    exclude_user_id=request.user.id,
)
```

**Harvest Report:**
```python
_notify_admins(
    f'Harvest reported for {rental.machine.name}: {total_harvest} sacks, BUFIA share {bufia_share} sacks.',
    rental.id,
    exclude_user_id=request.user.id,
)
```

**Operator Assignment:**
```python
UserNotification.objects.create(
    user=operator,
    notification_type='rental_approved',
    message=f'You have been assigned to operate {rental.machine.name} for {rental.user.get_full_name()}.',
    related_object_id=rental.id,
)
```

## Real-Time Synchronization

### Current Implementation
- Notifications created immediately in database
- Visible on next page load/refresh
- Transaction-safe with `@transaction.atomic`
- Row-level locking with `select_for_update()`

### Data Flow
```
Operator Action
     │
     v
Database Update (atomic)
     │
     v
Notification Created (bulk)
     │
     v
Admin Dashboard (on refresh)
     │
     v
Admin Sees Update
```

## Performance Metrics

### Notification Creation
- **Method:** Bulk create for multiple admins
- **Time Complexity:** O(n) where n = number of admins
- **Database Queries:** 2 (fetch admins, bulk create)
- **Performance:** Excellent

### Transaction Safety
- **Isolation Level:** Database default
- **Locking:** Row-level with `select_for_update()`
- **Rollback:** Automatic on error
- **Consistency:** Guaranteed

## Summary

✅ **Complete bidirectional communication**
✅ **Efficient bulk notifications**
✅ **Transaction-safe operations**
✅ **Clear, descriptive messages**
✅ **Proper error handling**
✅ **Production-ready implementation**

---

**Status:** All communication flows verified and working correctly.
