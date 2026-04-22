# One Machine Per User Restriction - Fixed

## Summary
Users can now only rent the same machine once **for overlapping dates**. They cannot have multiple active rentals for the same machine that overlap in time.

## Issue Fixed

### Previous Behavior (Bug):
- User had TRACTOR rental for April 22
- User tried to book TRACTOR for April 23
- ❌ **Blocked** - Even though dates don't overlap!

### New Behavior (Fixed):
- User has TRACTOR rental for April 22
- User tries to book TRACTOR for April 23
- ✅ **Allowed** - Dates don't overlap (April 22 ends before April 23 starts)

## Implementation

### Location
`machines/forms.py` - `RentalForm.clean()` method

### Validation Logic

Added **Validation 5** in the form's `clean()` method that checks:

1. **User Identification**: Gets the booking user (either the logged-in user or the selected member for admin bookings)

2. **Active Rental Check**: Searches for existing rentals where:
   - Same user (`user=booking_user`)
   - Same machine (`machine=machine`)
   - Active status (`status__in=['pending', 'approved', 'assigned']`)
   - Not cancelled or completed (`exclude workflow_state__in=['cancelled', 'completed']`)
   - **Overlapping dates** (`exclude Q(end_date__lt=start_date) | Q(start_date__gt=end_date)`)
   - Excluding the current rental being edited (`exclude pk=exclude_id`)

3. **Error Message**: If an overlapping active rental exists, shows:
   ```
   You already have an active rental for {machine_name} 
   (from {start_date} to {end_date}, Status: {status}) that overlaps with your requested dates. 
   Please choose different dates or wait until your current rental is completed.
   ```

### Code Added

```python
# Validation 5: Check if user already has an active rental for this machine
booking_user = self._resolved_booking_user if hasattr(self, '_resolved_booking_user') and self._resolved_booking_user else self.user
if booking_user:
    exclude_id = self.instance.pk if self.instance.pk else None
    existing_rental = Rental.objects.filter(
        user=booking_user,
        machine=machine,
        status__in=['pending', 'approved', 'assigned']
    ).exclude(
        pk=exclude_id
    ).exclude(
        workflow_state__in=['cancelled', 'completed']
    ).exclude(
        # Exclude rentals that don't overlap with the requested dates
        Q(end_date__lt=start_date) | Q(start_date__gt=end_date)
    ).first()
    
    if existing_rental:
        raise ValidationError(
            f'You already have an active rental for {machine.name} '
            f'(from {existing_rental.start_date} to {existing_rental.end_date}, '
            f'Status: {existing_rental.get_status_display()}) that overlaps with your requested dates. '
            f'Please choose different dates or wait until your current rental is completed.'
        )
```

## What This Prevents

### ❌ Blocked Scenarios:
1. User has TRACTOR rental April 22-24 → Cannot book TRACTOR April 23-25 (overlaps)
2. User has HARVESTER rental April 20-25 → Cannot book HARVESTER April 22-23 (overlaps)
3. User has TRANSPLANTER rental April 23 → Cannot book TRANSPLANTER April 23 (same date)

### ✅ Allowed Scenarios:
1. User has TRACTOR rental April 22 → **Can book TRACTOR April 23** (no overlap)
2. User has HARVESTER rental April 20-22 → **Can book HARVESTER April 23-25** (no overlap)
3. User's previous rental is **completed** → Can book the same machine again
4. User's previous rental is **cancelled** → Can book the same machine again
5. User booking a **different machine** → Always allowed
6. Admin editing an existing rental → Allowed (excludes current rental from check)

## Date Overlap Logic

Two rentals overlap if:
- Rental A starts before or on the day Rental B ends, AND
- Rental A ends after or on the day Rental B starts

Two rentals DON'T overlap if:
- Rental A ends before Rental B starts, OR
- Rental A starts after Rental B ends

### Examples:

**Overlap (Blocked):**
- Existing: April 22-24, New: April 23-25 ❌
- Existing: April 22-24, New: April 22-24 ❌
- Existing: April 22-24, New: April 21-23 ❌

**No Overlap (Allowed):**
- Existing: April 22, New: April 23 ✅
- Existing: April 22-24, New: April 25-27 ✅
- Existing: April 25-27, New: April 22-24 ✅

## Validation Order

The validations now run in this order:

1. ✅ End date must be after start date
2. ✅ Start date cannot be in the past
3. ✅ Maximum rental period (30 days)
4. ✅ Minimum advance booking (1 day for portal users)
5. ✅ **FIXED: User can only rent same machine once for overlapping dates**
6. ✅ Check machine availability (date conflicts with other users)
7. ✅ Check maintenance schedule

## User Experience

### For Regular Users:
- When trying to book a machine they already have an active rental for **with overlapping dates**
- Form validation fails with clear error message
- Message shows their existing rental details (dates and status)
- User can book the same machine for non-overlapping dates

### For Admins:
- Same validation applies when creating bookings for members
- Prevents accidental duplicate bookings with overlapping dates
- Can still edit existing rentals without triggering the validation

## Edge Cases Handled

1. **Admin Bookings**: Works for both member bookings and walk-in bookings
2. **Editing Rentals**: Excludes the current rental being edited from the check
3. **Multiple Machines**: Users can still rent different machines simultaneously
4. **Completed Rentals**: Users can rent the same machine again after completion
5. **Cancelled Rentals**: Users can rent the same machine again after cancellation
6. **Non-overlapping Dates**: Users can book the same machine for different dates
7. **Sequential Bookings**: User can book April 22, then April 23, then April 24 (no overlap)

## Testing Scenarios

### Test 1: Overlapping Dates (Blocked)
1. User books TRACTOR for April 22-24 (Status: Pending)
2. User tries to book TRACTOR for April 23-25
3. ❌ **Result**: Validation error - "You already have an active rental for TRACTOR that overlaps..."

### Test 2: Non-overlapping Dates (Allowed)
1. User books TRACTOR for April 22 (Status: Pending)
2. User tries to book TRACTOR for April 23
3. ✅ **Result**: Booking allowed (no overlap)

### Test 3: Sequential Bookings (Allowed)
1. User books TRACTOR for April 22-24 (Status: Approved)
2. User tries to book TRACTOR for April 25-27
3. ✅ **Result**: Booking allowed (no overlap)

### Test 4: After Completion (Allowed)
1. User books TRACTOR for April 22-24 (Status: Completed)
2. User tries to book TRACTOR for April 23-25
3. ✅ **Result**: Booking allowed (previous rental completed)

### Test 5: Different Machine (Allowed)
1. User books TRACTOR for April 22-24 (Status: Pending)
2. User tries to book HARVESTER for April 23-25
3. ✅ **Result**: Booking allowed (different machines)

### Test 6: Same Date (Blocked)
1. User books TRACTOR for April 23 (Status: Approved)
2. User tries to book TRACTOR for April 23
3. ❌ **Result**: Validation error (same date = overlap)

## Files Modified

- `machines/forms.py` - Fixed validation in `RentalForm.clean()` method

## Benefits

1. **Fair Access**: Prevents users from hogging machines with overlapping bookings
2. **Flexibility**: Users can book the same machine for different dates
3. **Clear Workflow**: Users understand they can't have overlapping bookings
4. **Sequential Bookings**: Users can book consecutive days without issues
5. **Better Resource Management**: Tracks active machine usage per user per time period

## Notes

- This restriction only applies to **active** rentals (pending, approved, assigned) **with overlapping dates**
- Users can have multiple **completed** or **cancelled** rentals for the same machine
- Users can still rent **multiple different machines** at the same time
- Users can book the **same machine for non-overlapping dates** (e.g., April 22, then April 23)
- The validation message clearly explains why the booking was blocked and what the user needs to do
- Each machine has its own conflict tracking - conflicts are machine-specific
