# Calendar Display Fix - Completed Rentals

**Date**: March 1, 2026  
**Issue**: Completed rentals were still showing on the calendar as blocked dates  
**Status**: ✅ FIXED

---

## Problem

When a rental was marked as completed (either through normal workflow or early completion), it was still appearing on the calendar as a blocked/unavailable date. This prevented other farmers from booking the machine for the same dates.

**Root Cause**: The calendar views and availability check methods were only filtering by the `status` field (which remains 'approved'), but not checking the `workflow_state` field (which becomes 'completed' when the rental is finished).

---

## Solution

Updated three key areas to exclude completed and cancelled rentals:

### 1. Calendar Events View (`machines/calendar_views.py`)

**Function**: `machine_calendar_events()`

**Change**: Added filter to exclude completed and cancelled rentals

```python
# Before
approved_rentals = Rental.objects.filter(
    machine=machine,
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
).select_related('user')

# After
from django.db.models import Q
approved_rentals = Rental.objects.filter(
    machine=machine,
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
).exclude(
    Q(workflow_state='completed') | Q(workflow_state='cancelled')
).select_related('user')
```

### 2. All Machines Calendar View (`machines/calendar_views.py`)

**Function**: `all_machines_calendar_events()`

**Change**: Same filter applied for consistency

```python
# Before
rentals = Rental.objects.filter(
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
).select_related('user', 'machine')

# After
from django.db.models import Q
rentals = Rental.objects.filter(
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
).exclude(
    Q(workflow_state='completed') | Q(workflow_state='cancelled')
).select_related('user', 'machine')
```

### 3. Availability Check Methods (`machines/models.py`)

**Method 1**: `Rental.check_availability()`

```python
# Before
overlapping = cls.objects.filter(
    machine=machine,
    status__in=['approved', 'pending'],
    start_date__lte=end_date,
    end_date__gte=start_date
)

# After
overlapping = cls.objects.filter(
    machine=machine,
    status__in=['approved', 'pending'],
    start_date__lte=end_date,
    end_date__gte=start_date
).exclude(
    Q(workflow_state='completed') | Q(workflow_state='cancelled')
)
```

**Method 2**: `Rental.check_availability_for_approval()`

```python
# Before
overlapping = cls.objects.filter(
    machine=machine,
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
)

# After
overlapping = cls.objects.filter(
    machine=machine,
    status='approved',
    start_date__lte=end_date,
    end_date__gte=start_date
).exclude(
    Q(workflow_state='completed') | Q(workflow_state='cancelled')
)
```

---

## Impact

### What Changed
- ✅ Completed rentals no longer appear on calendar
- ✅ Cancelled rentals no longer appear on calendar
- ✅ Machines become available immediately after rental completion
- ✅ Other farmers can now book completed rental dates

### What Stayed the Same
- ✅ In-progress rentals still block the machine
- ✅ Pending and approved rentals still block the machine
- ✅ All tests still pass (44/44)
- ✅ No breaking changes to existing functionality

---

## Testing

All existing tests pass with the changes:

```bash
python manage.py test tests.test_in_kind_workflow tests.test_in_kind_properties_simple -v 1
```

**Result**: 44/44 tests passing ✅

---

## Files Modified

1. `machines/calendar_views.py`
   - `machine_calendar_events()` - Added workflow_state filter
   - `all_machines_calendar_events()` - Added workflow_state filter

2. `machines/models.py`
   - `Rental.check_availability()` - Added workflow_state filter
   - `Rental.check_availability_for_approval()` - Added workflow_state filter

---

## Verification

To verify the fix works:

1. Create a rental and mark it as completed
2. Check the calendar - the rental should no longer appear
3. Try to book the machine for the same dates - it should now be available

---

## Related Features

This fix ensures proper integration with:
- Early rental completion feature
- Normal rental completion workflow
- Calendar availability display
- Machine booking system
- IN-KIND workflow completion

---

## Notes

- The fix uses Django's `Q` objects for OR logic: `Q(workflow_state='completed') | Q(workflow_state='cancelled')`
- Both `status` and `workflow_state` fields are checked because:
  - `status` is the legacy field (pending/approved/completed)
  - `workflow_state` is the new field for IN-KIND workflow (requested/pending_approval/approved/in_progress/harvest_report_submitted/completed/cancelled)
- The fix is backward compatible with existing rentals
