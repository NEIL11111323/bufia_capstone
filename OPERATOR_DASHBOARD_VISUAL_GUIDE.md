# Operator Dashboard - Visual Guide

## What Juan Will See When He Logs In

### Dashboard Header
```
┌─────────────────────────────────────────────────────────────┐
│ 🔧 My Assigned Jobs                                         │
│ Manage equipment operations and submit harvest reports      │
└─────────────────────────────────────────────────────────────┘
```

### Statistics Cards
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total        │ │ Active Jobs  │ │ In Progress  │ │ Completed    │
│ Assigned     │ │              │ │              │ │              │
│      7       │ │      5       │ │      0       │ │      2       │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Active Jobs Section

#### Job Card Example (IN-KIND Rental):
```
┌─────────────────────────────────────────────────────────────┐
│ HARVESTER 13                                                │
│ [IN-KIND Payment] [Approved] [Assigned]                     │
├─────────────────────────────────────────────────────────────┤
│ Member:    Joel Melendres                                   │
│ Dates:     Mar 13, 2026 - Mar 13, 2026                      │
│ Location:  Not specified                                    │
│ Area:      - hectares                                       │
├─────────────────────────────────────────────────────────────┤
│ ⚡ Quick Actions                                            │
│                                                              │
│ [Status Dropdown ▼]  [Update Status]                        │
│ [Add notes...]                                              │
│                                                              │
│ ─────────────────────────────────────────────────────────  │
│ 🌾 Submit Harvest                                           │
│ [Total sacks]  [Submit Harvest]                             │
└─────────────────────────────────────────────────────────────┘
```

#### Job Card Example (Cash Rental):
```
┌─────────────────────────────────────────────────────────────┐
│ TRACTOR                                                     │
│ [Cash Payment] [Approved] [Assigned]                        │
├─────────────────────────────────────────────────────────────┤
│ Member:    Neil Test                                        │
│ Dates:     Mar 4, 2026 - Mar 4, 2026                        │
│ Location:  Not specified                                    │
│ Area:      - hectares                                       │
├─────────────────────────────────────────────────────────────┤
│ ⚡ Quick Actions                                            │
│                                                              │
│ [Status Dropdown ▼]  [Update Status]                        │
│ [Add notes...]                                              │
└─────────────────────────────────────────────────────────────┘
```

### Completed Jobs Section
```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Completed Jobs                                           │
├─────────────────────────────────────────────────────────────┤
│ TRACTOR                                [Completed]          │
│ Member:    Joel Melendres                                   │
│ Dates:     Mar 13, 2026 - Mar 13, 2026                      │
├─────────────────────────────────────────────────────────────┤
│ HARVESTER 13                           [Completed]          │
│ Member:    Joel Melendres                                   │
│ Dates:     Mar 13, 2026 - Mar 13, 2026                      │
│ Harvest:   21.5 sacks                                       │
└─────────────────────────────────────────────────────────────┘
```

## Status Dropdown Options

When Juan clicks the status dropdown, he'll see:
```
┌─────────────────────────┐
│ Unassigned              │
│ Assigned            ✓   │ ← Currently selected
│ Traveling               │
│ Operating               │
│ Work Completed          │
│ Harvest Reported        │
└─────────────────────────┘
```

## Workflow Example

### Scenario: Operating a Harvester (IN-KIND)

**Step 1: Job Assigned**
```
Status: [Assigned]
Action: Review job details
```

**Step 2: Traveling to Field**
```
Status: [Traveling]
Notes: "On the way to Barangay San Jose"
Action: Click [Update Status]
```

**Step 3: Start Operating**
```
Status: [Operating]
Notes: "Started harvesting at 8:00 AM"
Action: Click [Update Status]
```

**Step 4: Complete Harvest**
```
Status: [Operating]
Total Harvest: 45.5 sacks
Action: Enter harvest amount, click [Submit Harvest]
```

**Step 5: System Calculates**
```
Total Harvest: 45.5 sacks
BUFIA Share: 5.06 sacks (1/9 ratio)
Member Share: 40.44 sacks
Status: [Harvest Reported]
```

**Step 6: Admin Verifies**
```
Admin confirms rice delivery
Rental marked as Completed
Job moves to "Completed Jobs" section
```

## Color Coding

### Badges:
- **Blue** = Payment Type (IN-KIND, Cash, Online, Face-to-Face)
- **Primary Blue** = Status (Approved, In Progress)
- **Dark** = Operator Status (Assigned, Traveling, Operating)
- **Green** = Completed
- **Warning Yellow** = Harvest Reported

### Cards:
- **White** = Active jobs
- **Light Gray** = Completed jobs
- **Yellow** = Action boxes (Quick Actions)
- **Green** = Success messages

## Empty State

If no jobs are assigned:
```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│                    📋                                        │
│                                                              │
│              No Active Jobs                                 │
│                                                              │
│     You don't have any active jobs assigned.                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Mobile View

The dashboard is responsive and works on mobile devices:
- Statistics stack vertically
- Job cards take full width
- Forms remain easy to use
- Buttons are touch-friendly

## Key Features

### ✅ What Operators CAN Do:
- View all assigned jobs
- Update job status
- Add notes about progress
- Submit harvest reports (IN-KIND)
- View completed jobs history

### ❌ What Operators CANNOT Do:
- Approve rentals (admin only)
- Assign jobs to themselves (admin only)
- Delete rentals (admin only)
- Modify payment amounts (admin only)
- Access admin dashboard (admin only)

## Quick Reference

### Common Actions:

**Update Status**:
1. Select new status from dropdown
2. Add notes (optional)
3. Click "Update Status"

**Submit Harvest**:
1. Enter total sacks harvested
2. Click "Submit Harvest"
3. System auto-calculates shares

**View Details**:
- All job information is visible in the card
- No need to click through multiple pages

## Tips for Operators

1. **Update status regularly** - Keep admin informed of progress
2. **Add detailed notes** - Help admin understand field conditions
3. **Submit harvest promptly** - Don't delay harvest reporting
4. **Check dashboard daily** - New jobs may be assigned
5. **Report issues immediately** - Use notes to communicate problems

---

**Dashboard URL**: http://127.0.0.1:8000/machines/operator/dashboard/
**Login**: operator1 / operator123
