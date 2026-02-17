# Rental Visibility Fix

## Problem
After approving or rejecting a rental from the review page, the rental would disappear from the dashboard. This happened because:
1. The default filter was set to "Pending" status
2. Once a rental was approved/rejected, it was no longer "Pending"
3. The page would reload with the default "Pending" filter, hiding the just-approved rental

## Solution
Changed the default status filter from "Pending" to "All Status" so that rentals remain visible after approval or rejection.

## Changes Made

### 1. Updated Default Filter (machines/admin_views.py)
**Before:**
```python
status_filter = request.GET.get('status', 'pending')
```

**After:**
```python
status_filter = request.GET.get('status', 'all')
```

This ensures that when the page loads without any filter parameters, it shows ALL rentals instead of just pending ones.

### 2. Updated Redirects (machines/admin_views.py)
Changed all redirects from `admin_rental_dashboard` to `rental_list`:

**In admin_approve_rental():**
```python
return redirect('machines:rental_list')
```

**In view_payment_proof():**
```python
return redirect('machines:rental_list')
```

This ensures consistency since we're now using rental_list as the main dashboard.

## Behavior Now

### Before Fix:
1. Admin views rental list (shows pending rentals by default)
2. Admin clicks "Review" on a rental
3. Admin approves the rental
4. Page redirects back to rental list
5. ❌ Rental disappears (because it's no longer pending and filter is set to "pending")

### After Fix:
1. Admin views rental list (shows ALL rentals by default)
2. Admin clicks "Review" on a rental
3. Admin approves the rental
4. Page redirects back to rental list
5. ✅ Rental is still visible (now showing as "Approved")

## Filter Options Still Available

Admins can still filter by:
- **Status**: All Status, Pending, Approved, Rejected
- **Payment**: All, Verified, Unverified, With Proof
- **Search**: By user name or machine name

The change only affects the DEFAULT view when no filter is selected.

## Benefits

1. **Better Visibility**: Admins can see the result of their actions immediately
2. **Confirmation**: Visual confirmation that the approval/rejection worked
3. **Context**: Can see both pending and processed rentals together
4. **Flexibility**: Can still filter to see only pending if desired

## Testing

To verify the fix:

1. **Test Approval:**
   - Go to rental list (should show all rentals)
   - Click "Review" on a pending rental
   - Approve it
   - Verify you're redirected back to rental list
   - Verify the rental is still visible with "Approved" status

2. **Test Rejection:**
   - Click "Review" on a pending rental
   - Reject it
   - Verify you're redirected back to rental list
   - Verify the rental is still visible with "Rejected" status

3. **Test Filtering:**
   - Use status filter to select "Pending"
   - Verify only pending rentals show
   - Approve one
   - Verify it disappears from the pending view (correct behavior)
   - Change filter back to "All Status"
   - Verify the approved rental is visible

## Files Modified
- machines/admin_views.py (changed default filter and redirects)

## Status
✅ Fix complete
✅ No syntax errors
✅ Ready for testing
