# Operator Navigation Summary

## What Each Link Does

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPERATOR NAVIGATION BAR                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR                                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 Dashboard                                                    │
│     └─ Shows: ALL assigned jobs (no filter)                     │
│     └─ URL: /machines/operator/dashboard/                       │
│     └─ Functions:                                                │
│        • View all your jobs                                      │
│        • Update job status                                       │
│        • Submit harvest reports                                  │
│        • See statistics                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ MY OPERATIONS                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📋 All Assigned Jobs                                            │
│     └─ Shows: ALL jobs (same as Dashboard)                      │
│     └─ URL: /machines/operator/dashboard/                       │
│     └─ Filter: None                                              │
│                                                                  │
│  🔄 In Progress                                                  │
│     └─ Shows: Jobs you're currently working on                  │
│     └─ URL: /machines/operator/dashboard/?status=in_progress    │
│     └─ Filter: Status = "Traveling" OR "Operating"              │
│     └─ Use: Focus on active work                                │
│                                                                  │
│  🌾 Awaiting Harvest                                             │
│     └─ Shows: IN-KIND jobs ready for harvest report             │
│     └─ URL: /machines/operator/dashboard/?status=awaiting_harvest│
│     └─ Filter: IN-KIND + Operating status                       │
│     └─ Use: Know which jobs need harvest reports                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ EQUIPMENT                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🚜 View Machines                                                │
│     └─ Shows: All machines in the system                        │
│     └─ URL: /machines/                                           │
│     └─ Functions:                                                │
│        • View machine details                                    │
│        • Check machine status                                    │
│        • See specifications                                      │
│     └─ Note: View only, cannot modify                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Page Content Breakdown

### 1. Dashboard / All Assigned Jobs
**Same page, two ways to access it**

```
┌────────────────────────────────────────────────────────┐
│  OPERATOR DASHBOARD                                     │
│  Manage your assigned equipment jobs                    │
├────────────────────────────────────────────────────────┤
│                                                         │
│  📊 STATISTICS                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │ Assigned │In Progress│ Awaiting │Completed │        │
│  │    5     │     2     │    1     │    3     │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
│                                                         │
│  📋 JOB CARDS (All Jobs)                                │
│  ┌─────────────────────────────────────────────┐       │
│  │ 🚜 Tractor - Juan Dela Cruz                 │       │
│  │ Jan 15 - Jan 20 | IN-KIND | Operating       │       │
│  ├─────────────────────────────────────────────┤       │
│  │ Machine: Tractor | Location: Field A        │       │
│  │ Area: 2.5 ha | Last Update: Jan 15, 10:00 AM│       │
│  ├─────────────────────────────────────────────┤       │
│  │ ⚡ QUICK ACTIONS                             │       │
│  │ ┌──────────────┬──────────────┐             │       │
│  │ │Update Status │Submit Harvest│             │       │
│  │ │[Dropdown]    │[Form]        │             │       │
│  │ │[Notes]       │              │             │       │
│  │ │[Update Btn]  │[Submit Btn]  │             │       │
│  │ └──────────────┴──────────────┘             │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  [More job cards...]                                    │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 2. In Progress
**Filtered view of dashboard**

```
┌────────────────────────────────────────────────────────┐
│  JOBS IN PROGRESS                                       │
│  Jobs currently being operated or traveled to           │
├────────────────────────────────────────────────────────┤
│                                                         │
│  📊 STATISTICS (Same as above)                          │
│                                                         │
│  📋 JOB CARDS (Filtered)                                │
│  Only shows jobs with status:                           │
│  • Traveling                                            │
│  • Operating                                            │
│                                                         │
│  [Job cards with same layout as above]                  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 3. Awaiting Harvest
**Filtered view for IN-KIND jobs**

```
┌────────────────────────────────────────────────────────┐
│  JOBS AWAITING HARVEST                                  │
│  IN-KIND jobs ready for harvest report submission       │
├────────────────────────────────────────────────────────┤
│                                                         │
│  📊 STATISTICS (Same as above)                          │
│                                                         │
│  📋 JOB CARDS (Filtered)                                │
│  Only shows jobs with:                                  │
│  • Payment Type = IN-KIND                               │
│  • Status = Operating                                   │
│  • Workflow = In Progress                               │
│                                                         │
│  [Job cards with harvest form highlighted]              │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 4. View Machines
**Different page - machine list**

```
┌────────────────────────────────────────────────────────┐
│  MACHINES                                               │
│  Browse available equipment                             │
├────────────────────────────────────────────────────────┤
│                                                         │
│  🚜 MACHINE LIST                                        │
│  ┌─────────────────────────────────────────────┐       │
│  │ 🚜 Tractor Model X                          │       │
│  │ Type: Tractor | Status: Available           │       │
│  │ [View Details]                              │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ 🌾 Harvester Model Y                        │       │
│  │ Type: Harvester | Status: In Use            │       │
│  │ [View Details]                              │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  [More machines...]                                     │
│                                                         │
└────────────────────────────────────────────────────────┘
```

## Functions Available on Each Page

### Dashboard Pages (All 3 views)
Each job card has TWO main functions:

#### Function 1: Update Job Status
```
┌─────────────────────────────────┐
│ Update Job Status               │
├─────────────────────────────────┤
│ Status: [Dropdown]              │
│         • Assigned              │
│         • Traveling             │
│         • Operating             │
│         • Harvest Reported      │
│                                 │
│ Notes: [Text area]              │
│        Add notes about progress │
│                                 │
│ [Update Status Button]          │
└─────────────────────────────────┘
```

#### Function 2: Submit Harvest Report (IN-KIND only)
```
┌─────────────────────────────────┐
│ Submit Harvest Report           │
├─────────────────────────────────┤
│ Total Harvest: [Number]         │
│                (e.g., 21.3)     │
│                                 │
│ Harvest Notes: [Text area]      │
│                (optional)       │
│                                 │
│ [Submit Harvest Button]         │
│                                 │
│ System auto-calculates:         │
│ • BUFIA Share (Total ÷ 9)       │
│ • Member Share (Total - BUFIA)  │
└─────────────────────────────────┘
```

### View Machines Page
- View machine details (read-only)
- Check machine status
- See specifications
- No modification allowed

## How Filtering Works

```python
# Base query: All assigned jobs
base_jobs = Rental.objects.filter(
    assigned_operator=request.user
).exclude(
    status__in=['completed', 'cancelled', 'rejected']
)

# Filter 1: In Progress
if status == 'in_progress':
    jobs = base_jobs.filter(
        operator_status__in=['traveling', 'operating']
    )

# Filter 2: Awaiting Harvest
if status == 'awaiting_harvest':
    jobs = base_jobs.filter(
        payment_type='in_kind',
        workflow_state='in_progress',
        operator_status='operating'
    )

# Default: All Jobs
else:
    jobs = base_jobs
```

## Statistics Always Show Full Count

The statistics cards at the top ALWAYS show counts for ALL jobs, regardless of which filter is active:

```
┌──────────┬──────────┬──────────┬──────────┐
│ Assigned │In Progress│ Awaiting │Completed │
│    5     │     2     │    1     │    3     │
└──────────┴──────────┴──────────┴──────────┘
     ↑           ↑           ↑          ↑
   Total      Traveling   IN-KIND    Harvest
   Jobs       Operating   Operating  Reported
```

## URL Structure

```
Base URL: /machines/operator/dashboard/

No parameters:
→ Shows all jobs

?status=in_progress:
→ Shows only traveling/operating jobs

?status=awaiting_harvest:
→ Shows only IN-KIND jobs ready for harvest

?status=completed:
→ Shows completed jobs (for reference)
```

## Key Points

1. **Same Template, Different Data**
   - All three "My Operations" links use the same template
   - Only the data (job list) changes based on filter
   - Statistics always show full counts

2. **Two Main Functions**
   - Update Status: Available for ALL jobs
   - Submit Harvest: Only for IN-KIND jobs

3. **View Machines is Different**
   - Completely different page
   - Shows machine list, not jobs
   - Read-only access

4. **Navigation Persists**
   - Sidebar stays visible on all pages
   - Active link is highlighted
   - Can switch between views easily

5. **Real-Time Updates**
   - Status changes are immediate
   - Harvest submissions notify admins
   - Timestamps are recorded automatically
