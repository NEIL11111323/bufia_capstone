# Reports Testing Checklist

## Server Status
✅ Development server running at: http://127.0.0.1:8000/
✅ No system check errors
✅ All report templates created
✅ Navigation menu updated

## Reports to Test

### 1. Rental Transactions Report
**URL:** http://127.0.0.1:8000/reports/rental/
**Features:**
- View all rental transactions
- Filter by date range, machine, member, status
- Statistics: Total rentals, completed, active, revenue
- Export to CSV
- Transaction ID display

**Test Steps:**
1. Login as admin
2. Navigate to Reports > Rental Transactions
3. Verify statistics cards display correctly
4. Test filters (date range, machine, member, status)
5. Click "Export CSV" button
6. Verify table shows all rental data

---

### 2. Harvest & BUFIA Share Report
**URL:** http://127.0.0.1:8000/reports/harvest/
**Features:**
- IN-KIND rental settlements
- BUFIA share calculation (floor(total_sacks / 9))
- Outstanding payments tracking
- Statistics: Total harvested, BUFIA share, member share, outstanding
- Export to CSV

**Test Steps:**
1. Navigate to Reports > Harvest & BUFIA Share
2. Verify statistics cards
3. Test date filters
4. Check harvest calculations (1 sack per 9 harvested)
5. Verify outstanding amounts
6. Export to CSV

---

### 3. Financial Summary Report
**URL:** http://127.0.0.1:8000/reports/financial/
**Features:**
- Total revenue breakdown
- Rental income vs membership income
- Payment method distribution (online vs face-to-face)
- Revenue visualization
- Recent payments list
- Export to CSV

**Test Steps:**
1. Navigate to Reports > Financial Summary
2. Verify total revenue calculation
3. Check rental income (from rentals)
4. Check membership income (₱500 × paid members)
5. Verify payment method distribution chart
6. Test date filters
7. Export to CSV

---

### 4. Membership Status Report
**URL:** http://127.0.0.1:8000/reports/membership/
**Features:**
- Member registration tracking
- Verification status
- Filter by status (all, active, pending, expired)
- Statistics: Total, active, pending, new members
- Member details table

**Test Steps:**
1. Navigate to Reports > Membership Status
2. Verify statistics cards
3. Test status filters (all, active, pending, expired)
4. Test date range filters
5. Verify member verification status badges
6. Check role display (Admin, Water Tender, Regular User)

---

### 5. Machine Usage Report
**URL:** http://127.0.0.1:8000/reports/machine-usage/
**Features:**
- Machine utilization tracking
- Rental count per machine
- Revenue per machine
- Maintenance records
- Utilization rate calculation
- Filter by machine and date range

**Test Steps:**
1. Navigate to Reports > Machine Usage
2. Verify usage statistics per machine
3. Test machine filter
4. Test date range filter
5. Check utilization rate calculations
6. Verify maintenance count

---

## Navigation Menu

The Reports dropdown in the sidebar now includes:
- ✅ Rental Transactions
- ✅ Harvest & BUFIA Share
- ✅ Financial Summary
- ✅ Membership Status
- ✅ Machine Usage
- ✅ Payment Management

## Common Issues to Check

### Template Errors
- [ ] No template syntax errors
- [ ] All variables render correctly
- [ ] No missing context data
- [ ] Filters work without errors

### Data Display
- [ ] Statistics cards show correct numbers
- [ ] Tables display data properly
- [ ] Empty states show when no data
- [ ] Date formatting is correct
- [ ] Currency formatting (₱) displays properly

### Filters
- [ ] Date range filters work
- [ ] Dropdown filters work
- [ ] Reset button clears filters
- [ ] Filters persist in export URLs

### Export Functionality
- [ ] CSV export includes all filtered data
- [ ] CSV headers are correct
- [ ] Filename includes timestamp
- [ ] Data formatting is correct in CSV

### Access Control
- [ ] Only admin/staff can access reports
- [ ] Non-admin users get redirected
- [ ] Login required for all report pages

## Expected Behavior

### Empty Data States
If you have no data yet, you should see:
- Empty tables with friendly messages
- Statistics showing 0
- No errors or crashes

### With Data
- All statistics should calculate correctly
- Tables should populate with real data
- Filters should narrow down results
- Exports should contain filtered data

## Quick Test Commands

```bash
# Check if server is running
# Open browser to: http://127.0.0.1:8000/

# Test each report URL directly:
http://127.0.0.1:8000/reports/rental/
http://127.0.0.1:8000/reports/harvest/
http://127.0.0.1:8000/reports/financial/
http://127.0.0.1:8000/reports/membership/
http://127.0.0.1:8000/reports/machine-usage/
```

## What to Report

If you encounter errors, please provide:
1. Which report page (URL)
2. What action you performed
3. Error message (if any)
4. Screenshot (if helpful)
5. Server console output

## Notes

- All reports are admin-only (@user_passes_test(is_admin))
- Reports use the same design system as the rest of the application
- All reports support CSV export
- Filters are optional - reports work without filters
- Empty states are handled gracefully
