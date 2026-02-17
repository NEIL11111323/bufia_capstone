# Notification Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NOTIFICATION SYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│     USER     │         │    ADMIN     │         │   DATABASE   │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │ 1. Create Request      │                        │
       ├───────────────────────────────────────────────>│
       │                        │                        │
       │                        │                        │
       │ 2. Signal: post_save   │                        │
       │    (created=True)      │                        │
       │<───────────────────────────────────────────────┤
       │                        │                        │
       │ 3. Notification:       │                        │
       │    "Request submitted" │                        │
       │<───────────────────────┤                        │
       │                        │                        │
       │                        │ 4. Notification:       │
       │                        │    "New request"       │
       │                        │<───────────────────────┤
       │                        │                        │
       │                        │ 5. Approve Request     │
       │                        ├───────────────────────>│
       │                        │                        │
       │                        │ 6. Signal: pre_save    │
       │                        │    (capture old status)│
       │                        │<───────────────────────┤
       │                        │                        │
       │                        │ 7. Signal: post_save   │
       │                        │    (status changed)    │
       │                        │<───────────────────────┤
       │                        │                        │
       │ 8. Notification:       │                        │
       │    "Request approved!" │                        │
       │<───────────────────────────────────────────────┤
       │                        │                        │
       │ 9. View Notification   │                        │
       │    (Bell Icon)         │                        │
       │<───────────────────────┤                        │
       │                        │                        │
```

## Signal Flow Detail

### 1. Request Creation Flow

```
User Action → Form Submit → Model.save()
                              ↓
                         post_save signal
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            User Notification    Admin Notification
            "Request submitted"  "New request from [User]"
```

### 2. Approval Flow

```
Admin Action → Change Status → Model.save()
                                   ↓
                              pre_save signal
                              (capture old status)
                                   ↓
                              post_save signal
                              (compare statuses)
                                   ↓
                         Status Changed? ──No──> End
                                   ↓
                                  Yes
                                   ↓
                          Create Notification
                          "Request approved!"
                                   ↓
                            User sees in UI
```

## Notification Types by Activity

### Machine Rentals

```
┌─────────────────┐
│  Rental Status  │
└────────┬────────┘
         │
    ┌────┴────┬────────┬──────────┬───────────┐
    ↓         ↓        ↓          ↓           ↓
 Created   Approved  Rejected  Completed  Cancelled
    │         │        │          │           │
    ↓         ↓        ↓          ↓           ↓
 User +    User      User       User        User
 Admin   Notified  Notified   Notified    Notified
Notified
```

### Rice Mill Appointments

```
┌──────────────────────┐
│ Appointment Status   │
└──────────┬───────────┘
           │
    ┌──────┴────┬────────┬──────────┬───────────┐
    ↓           ↓        ↓          ↓           ↓
 Created     Approved  Rejected  Completed  Cancelled
    │           │        │          │           │
    ↓           ↓        ↓          ↓           ↓
 User +      User      User       User        User
 Admin     Notified  Notified   Notified    Notified
Notified
(with ref#)
```

### Irrigation Requests

```
┌──────────────────────┐
│  Irrigation Status   │
└──────────┬───────────┘
           │
    ┌──────┴────┬────────┬──────────┬───────────┐
    ↓           ↓        ↓          ↓           ↓
 Created     Approved  Rejected  Completed  Cancelled
    │           │        │          │           │
    ↓           ↓        ↓          ↓           ↓
Farmer +    Farmer    Farmer     Farmer      Farmer
Admin +    Notified  Notified   Notified    Notified
Water                (+ reason)
Tender
Notified
```

## Bulk Action Flow

```
Admin selects multiple items
         ↓
Chooses bulk action (Approve/Reject/Complete)
         ↓
System iterates through each item
         ↓
    ┌────┴────┐
    ↓         ↓
 Item 1    Item 2    ... Item N
    ↓         ↓           ↓
 save()    save()     save()
    ↓         ↓           ↓
 Signal    Signal     Signal
    ↓         ↓           ↓
 Notify    Notify     Notify
 User 1    User 2     User N
```

## Notification Display Flow

```
User logs in
     ↓
Notification context processor runs
     ↓
Queries unread notifications
     ↓
Passes to template
     ↓
┌────────────────────────┐
│  Navigation Bar        │
│  ┌──────────────────┐  │
│  │  🔔 (Red Dot)    │  │ ← Shows if unread
│  └────────┬─────────┘  │
│           ↓            │
│  ┌──────────────────┐  │
│  │  Dropdown Menu   │  │
│  │  • Notification 1│  │
│  │  • Notification 2│  │
│  │  • Notification 3│  │
│  │  [View All]      │  │
│  └──────────────────┘  │
└────────────────────────┘
```

## Database Schema

```
┌─────────────────────────┐
│   UserNotification      │
├─────────────────────────┤
│ id (PK)                 │
│ user (FK → User)        │
│ notification_type       │
│ message                 │
│ timestamp               │
│ is_read                 │
└─────────────────────────┘
         ↑
         │ Foreign Key
         │
┌────────┴────────┐
│      User       │
├─────────────────┤
│ id (PK)         │
│ username        │
│ email           │
│ ...             │
└─────────────────┘
```

## Signal Registration

```
┌──────────────────────┐
│   Django App         │
│   (machines)         │
├──────────────────────┤
│  apps.py             │
│  ├─ MachinesConfig   │
│  └─ ready()          │
│     └─ import signals│
│                      │
│  signals.py          │
│  ├─ pre_save         │
│  └─ post_save        │
└──────────────────────┘
         ↓
    Registered at
    Django startup
         ↓
    Listens for
    Model.save()
```

## Key Components

1. **Signals** (`signals.py`)
   - Listen for model changes
   - Create notifications automatically

2. **Models** (`models.py`)
   - Rental, RiceMillAppointment, WaterIrrigationRequest
   - Status field triggers notifications

3. **Admin** (`admin.py`)
   - Bulk actions for approvals
   - Each action calls save() to trigger signals

4. **Views** (`views.py`)
   - Status changes call save()
   - Signals handle notification creation

5. **Templates** (`base.html`)
   - Notification dropdown
   - Red dot indicator
   - Real-time display

## Benefits

✅ **Automatic**: No manual notification code in views
✅ **Consistent**: All status changes trigger notifications
✅ **Maintainable**: Centralized in signal files
✅ **Scalable**: Easy to add new notification types
✅ **Reliable**: Django's signal system is battle-tested
