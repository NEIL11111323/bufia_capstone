# 📊 Operator System Workflow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATOR SYSTEM                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Dashboard   │  │  All Jobs    │  │ Ongoing Jobs │    │
│  │              │  │              │  │              │    │
│  │ • Stats      │  │ • List view  │  │ • Active     │    │
│  │ • Recent     │  │ • Filters    │  │ • Update     │    │
│  │ • Overview   │  │ • Details    │  │ • Notes      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Harvest    │  │ Completed    │  │ Notifications│    │
│  │              │  │              │  │              │    │
│  │ • Submit     │  │ • History    │  │ • Filters    │    │
│  │ • Calculate  │  │ • Results    │  │ • Mark read  │    │
│  │ • Track      │  │ • Archive    │  │ • Actions    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐                                          │
│  │   Machines   │                                          │
│  │              │                                          │
│  │ • View all   │                                          │
│  │ • Status     │                                          │
│  │ • Specs      │                                          │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

## Job Status Flow

```
┌─────────────┐
│   ADMIN     │
│  Assigns    │
│   Job to    │
│  Operator   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                  OPERATOR WORKFLOW                      │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  ASSIGNED   │ ◄─── Operator receives notification
│             │      "New job assigned"
└──────┬──────┘
       │
       │ Operator updates status
       ▼
┌─────────────┐
│  TRAVELING  │ ◄─── "On the way to site"
│             │      Admin notified
└──────┬──────┘
       │
       │ Operator updates status
       ▼
┌─────────────┐
│  OPERATING  │ ◄─── "Currently working"
│             │      Admin notified
└──────┬──────┘      Machine status: "rented"
       │
       │
       ├─────────────┬─────────────┐
       │             │             │
       ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ CASH        │ │  IN-KIND    │ │  DECISION   │
│ PAYMENT     │ │  PAYMENT    │ │  MAKING     │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │             │             │
       │             ▼             │
       │      ┌─────────────┐     │
       │      │   HARVEST   │     │
       │      │   READY     │     │
       │      └──────┬──────┘     │
       │             │             │
       │             ▼             │
       │      ┌─────────────┐     │
       │      │   SUBMIT    │     │
       │      │   HARVEST   │     │
       │      │   REPORT    │     │
       │      └──────┬──────┘     │
       │             │             │
       │             ▼             │
       │      ┌─────────────┐     │
       │      │    ADMIN    │     │
       │      │   REVIEWS   │     │
       │      └──────┬──────┘     │
       │             │             │
       └─────────────┴─────────────┘
                     │
                     ▼
              ┌─────────────┐
              │  COMPLETED  │ ◄─── Admin marks complete
              │             │      Operator notified
              └─────────────┘      Machine freed
```

## Decision Making Flow

```
┌─────────────────────────────────────────────────────────┐
│              OPERATOR DECISIONS                         │
└─────────────────────────────────────────────────────────┘
       │
       ├─────────┬─────────┬─────────┬─────────┐
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  DELAY   │ │  CANCEL  │ │  MODIFY  │ │ SUPPORT  │ │  REPORT  │
│   JOB    │ │   JOB    │ │ SCHEDULE │ │ REQUEST  │ │  ISSUE   │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │            │
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────┐
│              ADMIN NOTIFICATION                         │
│                                                         │
│  • Operator decision logged                            │
│  • Admin receives notification                         │
│  • Member notified (if applicable)                     │
│  • System updated automatically                        │
└─────────────────────────────────────────────────────────┘
```

## Notification Flow

```
┌─────────────────────────────────────────────────────────┐
│                 NOTIFICATION TYPES                      │
└─────────────────────────────────────────────────────────┘
       │
       ├─────────┬─────────┬─────────┬─────────┐
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   JOB    │ │   JOB    │ │ HARVEST  │ │ HARVEST  │ │  URGENT  │
│ ASSIGNED │ │ UPDATED  │ │ APPROVED │ │ REJECTED │ │   JOB    │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │            │
     └────────────┴────────────┴────────────┴────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   OPERATOR       │
                    │   NOTIFICATIONS  │
                    │                  │
                    │  • Filter by type│
                    │  • Mark as read  │
                    │  • Take action   │
                    └──────────────────┘
```

## Harvest Reporting Flow

```
┌─────────────────────────────────────────────────────────┐
│              HARVEST REPORTING WORKFLOW                 │
└─────────────────────────────────────────────────────────┘

1. JOB COMPLETION
   ┌──────────────────┐
   │ Operator finishes│
   │ harvesting job   │
   └────────┬─────────┘
            │
            ▼
2. SUBMIT REPORT
   ┌──────────────────┐
   │ Enter total sacks│
   │ Add notes        │
   │ Submit to admin  │
   └────────┬─────────┘
            │
            ▼
3. AUTO CALCULATION
   ┌──────────────────┐
   │ System calculates│
   │ • BUFIA share    │
   │ • Member share   │
   └────────┬─────────┘
            │
            ▼
4. ADMIN REVIEW
   ┌──────────────────┐
   │ Admin reviews    │
   │ • Approves       │
   │ • OR Rejects     │
   └────────┬─────────┘
            │
            ├─────────────┬─────────────┐
            │             │             │
            ▼             ▼             ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │   APPROVED   │ │   REJECTED   │ │   PENDING    │
   │              │ │              │ │              │
   │ • Operator   │ │ • Operator   │ │ • Waiting    │
   │   notified   │ │   notified   │ │   for admin  │
   │ • Payment    │ │ • Resubmit   │ │              │
   │   processed  │ │   required   │ │              │
   └──────────────┘ └──────────────┘ └──────────────┘
```

## User Roles & Access

```
┌─────────────────────────────────────────────────────────┐
│                    SYSTEM ROLES                         │
└─────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    ADMIN     │     │   OPERATOR   │     │    MEMBER    │
│              │     │              │     │              │
│ • Full access│     │ • Dashboard  │     │ • Dashboard  │
│ • Assign jobs│     │ • View jobs  │     │ • Book       │
│ • Approve    │     │ • Update     │     │   machines   │
│ • Reports    │     │ • Harvest    │     │ • View       │
│ • Settings   │     │ • Notify     │     │   rentals    │
│              │     │ • Decide     │     │ • Pay        │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  BUFIA SYSTEM    │
                  │                  │
                  │ • Equipment      │
                  │ • Scheduling     │
                  │ • Payments       │
                  │ • Notifications  │
                  └──────────────────┘
```

## Navigation Structure

```
OPERATOR SIDEBAR MENU
├── Dashboard
│   └── Statistics & Recent Jobs
├── Jobs
│   ├── All Jobs
│   ├── Ongoing Jobs
│   ├── Awaiting Harvest
│   └── Completed Jobs
├── Other
│   ├── View Machines
│   └── Notifications
└── Profile
    └── Logout
```

## Data Flow

```
┌─────────────┐
│   ADMIN     │
└──────┬──────┘
       │ Assigns job
       ▼
┌─────────────┐
│  DATABASE   │
│  (Rental)   │
└──────┬──────┘
       │ Triggers notification
       ▼
┌─────────────┐
│ OPERATOR    │
│ NOTIFICATION│
└──────┬──────┘
       │ Operator views
       ▼
┌─────────────┐
│  OPERATOR   │
│  DASHBOARD  │
└──────┬──────┘
       │ Updates status
       ▼
┌─────────────┐
│  DATABASE   │
│  (Updated)  │
└──────┬──────┘
       │ Triggers notification
       ▼
┌─────────────┐
│   ADMIN     │
│ NOTIFICATION│
└─────────────┘
```

---

This diagram shows the complete operator system workflow, including job management, decision making, harvest reporting, and notification flows.
