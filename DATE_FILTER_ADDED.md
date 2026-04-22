# Date Filter Added to Admin Equipment Rentals

## Summary
Added a date filter to the Admin Equipment Rentals dashboard so admins can easily check rentals for specific time periods.

## New Filter Options

### Date Filter Dropdown:
- **All Dates** - Show all rentals (default)
- **Today** - Show rentals for today only
- **Tomorrow** - Show rentals for tomorrow
- **This Week** - Show rentals for the current week
- **This Month** - Show rentals for the current month

## How It Works

### Date Matching Logic:

The filter shows rentals where the rental period **overlaps** with the selected time period:

1. **Today**: Shows rentals where:
   - Start date is today, OR
   - End date is today, OR
   - Rental spans across today (starts before and ends after)

2. **Tomorrow**: Shows rentals where:
   - Start date is tomorrow, OR
   - End date is tomorrow, OR
   - Rental spans across tomorrow

3. **This Week**: Shows rentals that overlap with the current week (Monday to Sunday)

4. **This Month**: Shows rentals that overlap with the current month

### Examples:

**Today is April 23:**
- Rental April 23 → ✅ Shows in "Today"
- Rental April 22-24 → ✅ Shows in "Today" (spans across today)
- Rental April 23-25 → ✅ Shows in "Today" (starts today)
- Rental April 21-23 → ✅ Shows in "Today" (ends today)
- Rental April 24 → ❌ Not in "Today" (shows in "Tomorrow")

**This Week (April 21-27):**
- Rental April 23 → ✅ Shows in "This Week"
- Rental April 20-22 → ✅ Shows in "This Week" (overlaps)
- Rental April 26-28 → ✅ Shows in "This Week" (overlaps)
- Rental April 28-30 → ❌ Not in "This Week"

## Implementation

### Backend Changes (`machines/admin_views.py`)

Added date filter logic in `admin_rental_dashboard` view:

```python
date_filter = request.GET.get('date', 'all')
date_filter_labels = {
    'all': 'All Dates',
    'today': 'Today',
    'tomorrow': 'Tomorrow',
    'this_week': 'This Week',
    'this_month': 'This Month',
}

# Date filter
today = timezone.localdate()
if date_filter == 'today':
    filtered_rentals = filtered_rentals.filter(
        Q(start_date=today) | Q(end_date=today) | 
        Q(start_date__lte=today, end_date__gte=today)
    )
elif date_filter == 'tomorrow':
    tomorrow = today + timedelta(days=1)
    filtered_rentals = filtered_rentals.filter(
        Q(start_date=tomorrow) | Q(end_date=tomorrow) |
        Q(start_date__lte=tomorrow, end_date__gte=tomorrow)
    )
elif date_filter == 'this_week':
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    filtered_rentals = filtered_rentals.filter(
        Q(start_date__lte=week_end, end_date__gte=week_start)
    )
elif date_filter == 'this_month':
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    filtered_rentals = filtered_rentals.filter(
        Q(start_date__lte=month_end, end_date__gte=month_start)
    )
```

### Frontend Changes (`templates/machines/admin/rental_dashboard.html`)

Added date filter dropdown in the filter form:

```html
<div class="col-lg-auto col-md-4">
    <label class="form-label form-label-sm">Date</label>
    <select name="date" class="form-select form-select-sm">
        <option value="all" {% if date_filter == 'all' %}selected{% endif %}>All Dates</option>
        <option value="today" {% if date_filter == 'today' %}selected{% endif %}>Today</option>
        <option value="tomorrow" {% if date_filter == 'tomorrow' %}selected{% endif %}>Tomorrow</option>
        <option value="this_week" {% if date_filter == 'this_week' %}selected{% endif %}>This Week</option>
        <option value="this_month" {% if date_filter == 'this_month' %}selected{% endif %}>This Month</option>
    </select>
</div>
```

## User Experience

### Filter Bar Layout:
```
[Status ▼] [Payment ▼] [Date ▼] [Search...] [Apply] [Reset]
```

### Filter Combinations:
Admins can combine filters for powerful queries:

1. **Today's pending rentals**:
   - Status: Pending
   - Date: Today
   - Result: All pending rentals for today

2. **This week's Gcash payments**:
   - Payment: Gcash
   - Date: This Week
   - Result: All Gcash rentals for this week

3. **Today's TRACTOR rentals**:
   - Date: Today
   - Search: TRACTOR
   - Result: All TRACTOR rentals for today

### Filter Summary:
When filters are applied, a summary shows:
```
Tab: Pending | Status: All | Payment: All | Date: Today | Search: TRACTOR
```

## Use Cases

### Daily Operations:
1. **Morning Check**: Filter by "Today" to see all rentals scheduled for today
2. **Pickup Tracking**: Check which machines need to be picked up today
3. **Return Tracking**: See which machines are due back today

### Planning:
1. **Tomorrow's Schedule**: Filter by "Tomorrow" to prepare for next day
2. **Weekly Overview**: Filter by "This Week" to see the week's workload
3. **Monthly Report**: Filter by "This Month" for monthly statistics

### Quick Checks:
1. **Today's Pending**: Status=Pending + Date=Today
2. **Today's Gcash**: Payment=Gcash + Date=Today
3. **This Week's Completed**: Status=Completed + Date=This Week

## Benefits

1. **Quick Access**: One-click filter to see today's rentals
2. **Better Planning**: Easy to see upcoming rentals (tomorrow, this week)
3. **Efficient Workflow**: No need to scroll through all rentals
4. **Combined Filters**: Works with existing status, payment, and search filters
5. **Clear Display**: Filter summary shows active date filter

## Technical Details

### Date Range Calculation:
- **Week**: Monday (weekday 0) to Sunday (weekday 6)
- **Month**: First day to last day of current month
- **Overlap Detection**: Uses SQL queries to find rentals that overlap with the time period

### Query Optimization:
- Uses database-level filtering (efficient)
- Combines with existing filters (status, payment, search)
- Maintains pagination for large result sets

## Files Modified

1. `machines/admin_views.py` - Added date filter logic
2. `templates/machines/admin/rental_dashboard.html` - Added date filter dropdown

## Testing Scenarios

### Test 1: Today Filter
1. Create rental for today (April 23)
2. Create rental for tomorrow (April 24)
3. Filter by "Today"
4. ✅ **Result**: Only April 23 rental shows

### Test 2: This Week Filter
1. Create rentals for different days of the week
2. Filter by "This Week"
3. ✅ **Result**: All rentals within current week show

### Test 3: Combined Filters
1. Create multiple rentals with different statuses and dates
2. Filter: Status=Pending, Date=Today
3. ✅ **Result**: Only pending rentals for today show

### Test 4: Spanning Rentals
1. Create rental April 22-24 (spans across April 23)
2. Filter by "Today" (April 23)
3. ✅ **Result**: Rental shows (overlaps with today)

## Notes

- Date filter works with all rental statuses (pending, approved, completed, etc.)
- Combines seamlessly with existing filters
- Filter persists when navigating between tabs
- Reset button clears all filters including date
- Filter summary shows current date selection
