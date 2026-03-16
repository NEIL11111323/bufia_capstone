# Operator Navigation Guide

## Overview
Operators have a simplified navigation bar showing only their essential functions for equipment operations.

## Operator Navigation Structure

### Section 1: Operator
- **Dashboard** - Main operator dashboard with statistics and job overview

### Section 2: My Operations
- **All Assigned Jobs** - View all jobs assigned to you
- **In Progress** - Jobs currently being operated
- **Awaiting Harvest** - IN-KIND rentals ready for harvest reporting
- **Completed** - Finished jobs with harvest reports submitted

### Section 3: Equipment
- **View Machines** - Browse available machines and their specifications

### Section 4: Account
- **Notifications** - View system notifications and updates
- **Logout** - Sign out of the system

## What Operators See vs What They Don't See

### ✅ Operators CAN See:
- Dashboard (operator-specific)
- Assigned Jobs (all statuses)
- In Progress jobs
- Awaiting Harvest jobs
- Completed jobs
- Machine list
- Notifications
- Logout

### ❌ Operators CANNOT See:
- Equipment Rentals (member view)
- Rice Mill Appointments
- Maintenance Records
- Water Irrigation
- Reports & Analytics
- Administration
- Admin Panel
- Member Management
- Send Notifications
- Activity Logs

## Navigation Behavior

### Auto-Hiding
When an operator logs in, the system automatically:
1. Detects user is staff but not superuser
2. Hides all non-operator navigation sections
3. Shows only operator-relevant menu items
4. Maintains clean, focused interface

### Active States
Navigation items highlight when active:
- Dashboard - Active when on `/machines/operator/dashboard/`
- All Assigned Jobs - Active when no filter applied
- In Progress - Active when `?status=in_progress`
- Awaiting Harvest - Active when `?status=awaiting_harvest`
- Completed - Active when `?status=completed`
- View Machines - Active when on machine list page

## URL Structure

| Navigation Item | URL | Description |
|----------------|-----|-------------|
| Dashboard | `/machines/operator/dashboard/` | Main operator dashboard |
| All Assigned Jobs | `/machines/operator/dashboard/` | All jobs (no filter) |
| In Progress | `/machines/operator/dashboard/?status=in_progress` | Active operations |
| Awaiting Harvest | `/machines/operator/dashboard/?status=awaiting_harvest` | Ready for harvest |
| Completed | `/machines/operator/dashboard/?status=completed` | Finished jobs |
| View Machines | `/machines/` | Machine catalog |
| Notifications | `/notifications/` | System notifications |
| Logout | `/accounts/logout/` | Sign out |

## Implementation Details

### Template: `operator_dashboard_clean.html`
- Adds `operator-view` class to body
- JavaScript hides non-operator sections
- Maintains responsive design
- Clean, focused interface

### CSS Classes:
```css
body.operator-view .sidebar:not(.operator-sidebar) {
    display: none;
}
```

### JavaScript Logic:
```javascript
// Keeps only: Operator, My Operations, Equipment, Account sections
const keepSections = ['Operator', 'My Operations', 'Equipment', 'Account'];
```

## User Experience

### For Operators:
1. Login with operator credentials
2. See only relevant navigation items
3. Focus on assigned jobs
4. Quick access to harvest submission
5. No distractions from admin functions

### For Admins:
1. Login with admin credentials
2. See full navigation (unchanged)
3. Access all system functions
4. Can still view operator dashboard if needed

## Benefits

### Simplified Interface
- ✅ Reduces cognitive load
- ✅ Faster navigation
- ✅ Clear focus on operations
- ✅ Less training required

### Security
- ✅ Hides admin functions
- ✅ Prevents accidental access
- ✅ Clear role separation
- ✅ Maintains permissions

### Efficiency
- ✅ Quick job access
- ✅ Direct harvest submission
- ✅ Status filtering
- ✅ Streamlined workflow

## Customization

### Adding New Operator Navigation Items:

1. Edit `operator_dashboard_clean.html`
2. Add to `keepSections` array:
```javascript
const keepSections = ['Operator', 'My Operations', 'Equipment', 'Account', 'New Section'];
```

3. Add navigation item in base.html under operator condition

### Changing Navigation Order:

Modify the order in `keepSections` array to change display order.

## Troubleshooting

### Navigation not hiding
**Problem**: Operator sees all navigation items  
**Solution**: Check if `operator-view` class is added to body tag

### Wrong items showing
**Problem**: Incorrect sections visible  
**Solution**: Verify `keepSections` array in JavaScript

### Active states not working
**Problem**: Navigation items don't highlight  
**Solution**: Check URL patterns in template conditions

## Testing

### Test as Operator:
1. Login as `operator1` / `operator123`
2. Verify only 4 sections visible
3. Check all links work correctly
4. Test filtering (In Progress, Awaiting Harvest, etc.)

### Test as Admin:
1. Login as admin
2. Verify full navigation visible
3. Confirm operator dashboard still accessible
4. Check no interference with admin functions

## Related Files

- `templates/machines/operator/operator_dashboard_clean.html` - Main dashboard
- `templates/includes/operator_sidebar.html` - Operator sidebar (optional)
- `templates/base.html` - Base template with full navigation
- `machines/operator_views.py` - Operator view functions
- `fix_operator_permissions.py` - Account setup script

## Future Enhancements

### Potential Additions:
- Job calendar view
- Equipment maintenance alerts
- Performance statistics
- Harvest history
- Weather integration
- Route optimization

### Requested Features:
- Mobile app version
- Offline mode
- Photo upload for harvest
- GPS tracking
- Real-time updates
