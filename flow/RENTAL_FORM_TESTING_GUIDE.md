# Machine Rental Form - Testing Guide

## ✅ All Issues Fixed!

The machine rental form now works smoothly. Here's how to test it:

## Quick Test (2 minutes)

1. **Open your browser** and go to: http://127.0.0.1:8000/machines/
2. **Click "Rent"** on any available machine
3. **Fill out the form**:
   - Requester name should be pre-filled
   - Enter a farm location (e.g., "North Field")
   - Select operator type (My Own or BUFIA)
   - Pick start and end dates
   - Enter land dimensions (e.g., Length: 100, Width: 50)
   - Watch the area calculate automatically!
   - See the cost update in real-time
4. **Click "Submit Request"**
5. **Success!** You should be redirected to the payment page

## Detailed Testing Scenarios

### Scenario 1: Rent a 4-Wheel Drive Tractor
**Expected**: Per-hectare pricing (₱4,000/hectare)

1. Go to machines list
2. Find "4wheel Drive Tractor"
3. Click "Rent"
4. Fill in:
   - Farm Area: "Main Field"
   - Operator: My Own
   - Dates: Tomorrow to 3 days from now
   - Length: 200m
   - Width: 50m
   - Area: Should show 1.0000 hectares
5. Cost should show: ₱4,000.00
6. Submit successfully

### Scenario 2: Rent a Hand Tractor
**Expected**: Flat fee pricing

1. Go to machines list
2. Find "Hand tractor"
3. Click "Rent"
4. Fill in:
   - Farm Area: "South Field"
   - Operator: BUFIA
   - Dates: Tomorrow to 2 days from now
5. Cost should show flat fee (no area calculation needed)
6. Submit successfully

### Scenario 3: Rent a Harvester
**Expected**: Sack-based payment (1 sack per 9 sacks)

1. Go to machines list
2. Find "Harvester"
3. Click "Rent"
4. Fill in:
   - Farm Area: "East Field"
   - Operator: My Own
   - Dates: Tomorrow
   - Length: 150m
   - Width: 100m
   - Expected Yield: 90 sacks
5. Cost should show: 10 sacks of rice
6. Submit successfully

### Scenario 4: Try to Rent Rice Mill
**Expected**: Redirect to appointment booking

1. Go to machines list
2. Find "Rice Mill" (if available)
3. Click "Rent"
4. Should automatically redirect to appointment booking page
5. Message should explain rice mills need appointments

### Scenario 5: Create Rental Without Pre-Selected Machine
**Expected**: Can select any available machine

1. Go to: http://127.0.0.1:8000/machines/rentals/create/
2. Service Type dropdown should show all machines
3. Select any available machine
4. Fill out the rest of the form
5. Submit successfully

### Scenario 6: Test Form Validation
**Expected**: Proper error messages

1. Go to any rental form
2. Try to submit without filling required fields
3. Should see:
   - Red borders on invalid fields
   - Shake animation on invalid fields
   - Toast notification with error message
4. Fill in the fields
5. Try to set end date before start date
6. Should see validation error
7. Fix the dates
8. Submit successfully

### Scenario 7: Test Dynamic Cost Calculation
**Expected**: Cost updates as you type

1. Go to any rental form (except hand tractor)
2. Enter land dimensions:
   - Type length: 100
   - Watch area calculate
   - Type width: 50
   - Watch area update to 0.5000 hectares
3. Change dates:
   - Set start date to tomorrow
   - Set end date to 3 days from now
   - Watch "Rental Period" update to "3 days"
   - Watch cost update
4. Change dimensions again:
   - Update length to 200
   - Watch area update to 1.0000 hectares
   - Watch cost double

### Scenario 8: Test Different Operator Types
**Expected**: Radio buttons work smoothly

1. Go to any rental form
2. Click "My Own Operator"
   - Should highlight with green background
   - Should show ripple animation
3. Click "BUFIA Operator"
   - Should switch highlight
   - Should show ripple animation
4. Submit form
5. Check that operator choice is saved

## What to Look For

### ✅ Good Signs
- All fields are editable
- Date pickers open and work
- Area calculates automatically from length × width
- Cost updates when you change inputs
- Form submits without errors
- You're redirected to payment page
- Success message appears

### ❌ Bad Signs (Should NOT happen)
- Fields are disabled or grayed out
- Can't type in input fields
- Date pickers don't open
- Area stays at 0 when you enter dimensions
- Cost doesn't update
- Form won't submit
- JavaScript errors in browser console

## Browser Console Check

1. Open browser developer tools (F12)
2. Go to Console tab
3. Navigate to rental form
4. Should see NO red errors
5. May see some info messages (that's OK)

## Common Issues & Solutions

### Issue: "Service Type dropdown is empty"
**Solution**: Make sure you have machines in the database. Go to admin panel and add some machines.

### Issue: "Can't access rental form"
**Solution**: Make sure you're logged in and your membership is approved (verified member).

### Issue: "Form submits but nothing happens"
**Solution**: Check the browser console for errors. Make sure the payment system is configured.

### Issue: "Cost shows ₱0.00"
**Solution**: Make sure you've entered valid dates and dimensions. The cost calculator needs this data.

## Success Criteria

The rental form is working correctly if:

1. ✅ You can access the form
2. ✅ All fields are visible and editable
3. ✅ Date pickers work
4. ✅ Area calculates from dimensions
5. ✅ Cost updates dynamically
6. ✅ Form validates properly
7. ✅ Form submits successfully
8. ✅ You're redirected to payment
9. ✅ No JavaScript errors in console
10. ✅ Works for all machine types

## Need Help?

If you encounter any issues:

1. Check the browser console for errors (F12 → Console)
2. Check the Django server output for errors
3. Verify you're logged in as a verified member
4. Make sure machines exist in the database
5. Try a different browser
6. Clear browser cache and reload

## Status: ✅ ALL TESTS SHOULD PASS

The rental form has been completely fixed and should work smoothly for all scenarios!
