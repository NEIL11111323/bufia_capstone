# ✅ Operator System Testing Checklist

## Pre-Testing Setup

- [ ] Run `python test_operator_system.py` to verify system readiness
- [ ] Create operator account: `python create_operator.py`
- [ ] Verify operator credentials work
- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Restart Django development server

## 1. Authentication & Access

- [ ] Login as operator (username: operator, password: operator123)
- [ ] Verify operator navigation appears in sidebar
- [ ] Verify 7 navigation items visible
- [ ] Verify no admin menu items visible
- [ ] Logout and verify redirect works

## 2. Dashboard Testing

- [ ] Navigate to `/machines/operator/dashboard/`
- [ ] Verify statistics display correctly:
  - [ ] Active jobs count
  - [ ] In progress jobs count
  - [ ] Completed jobs count
- [ ] Verify recent jobs cards display
- [ ] Verify "View All" button works
- [ ] Verify responsive design on mobile

## 3. All Jobs Page

- [ ] Navigate to `/machines/operator/jobs/`
- [ ] Verify all assigned jobs display
- [ ] Verify job cards show:
  - [ ] Machine name
  - [ ] Member name
  - [ ] Date
  - [ ] Location (if available)
  - [ ] Area (if available)
  - [ ] Payment type badge
  - [ ] Status badge
- [ ] Click "View Details" button
- [ ] Verify navigation to job detail page

## 4. Job Detail Page

- [ ] Navigate to a specific job
- [ ] Verify job information displays:
  - [ ] Machine name
  - [ ] Member name
  - [ ] Date
  - [ ] Status
  - [ ] Location
  - [ ] Area
  - [ ] Payment type
  - [ ] Notes (if any)
- [ ] Test status update form:
  - [ ] Select new status
  - [ ] Add notes
  - [ ] Submit form
  - [ ] Verify success message
  - [ ] Verify status updated in database
- [ ] Test harvest form (for in-kind jobs):
  - [ ] Enter harvest total
  - [ ] Add notes
  - [ ] Submit form
  - [ ] Verify success message
- [ ] Click "Back to Jobs" button

## 5. Ongoing Jobs Page

- [ ] Navigate to `/machines/operator/jobs/ongoing/`
- [ ] Verify only active jobs display
- [ ] Verify jobs in "assigned", "traveling", "operating" status
- [ ] Test status update from this page
- [ ] Verify completed/cancelled jobs don't show

## 6. Awaiting Harvest Page

- [ ] Navigate to `/machines/operator/jobs/awaiting-harvest/`
- [ ] Verify only in-kind payment jobs display
- [ ] Verify harvest submission form appears
- [ ] Test harvest submission:
  - [ ] Enter total sacks
  - [ ] Add notes
  - [ ] Submit
  - [ ] Verify success message
  - [ ] Verify "Reported" badge appears
- [ ] Verify already reported jobs show status

## 7. Completed Jobs Page

- [ ] Navigate to `/machines/operator/jobs/completed/`
- [ ] Verify only completed jobs display
- [ ] Verify job history shows correctly
- [ ] Verify no action buttons appear
- [ ] Verify harvest totals display (for in-kind)

## 8. View Machines Page

- [ ] Navigate to `/machines/operator/machines/`
- [ ] Verify all machines display in grid
- [ ] Verify machine cards show:
  - [ ] Machine image (or placeholder)
  - [ ] Machine name
  - [ ] Machine type
  - [ ] Model (if available)
  - [ ] Year (if available)
  - [ ] Status badge
- [ ] Verify status colors:
  - [ ] Available (green)
  - [ ] Rented (yellow)
  - [ ] Maintenance (red)
- [ ] Verify responsive grid layout

## 9. Notifications Page

- [ ] Navigate to `/machines/operator/notifications/`
- [ ] Verify notifications display
- [ ] Test filter tabs:
  - [ ] All
  - [ ] Unread
  - [ ] Job Assignments
  - [ ] Harvest
  - [ ] Urgent
- [ ] Test "Mark as Read" button
- [ ] Test "Mark All Read" button
- [ ] Verify unread count updates
- [ ] Verify pagination (if >20 notifications)
- [ ] Click notification to view details

## 10. Navigation Testing

- [ ] Test all sidebar links:
  - [ ] Dashboard
  - [ ] All Jobs
  - [ ] Ongoing Jobs
  - [ ] Awaiting Harvest
  - [ ] Completed Jobs
  - [ ] View Machines
  - [ ] Notifications
- [ ] Verify active state highlighting
- [ ] Test sidebar collapse (desktop)
- [ ] Test sidebar toggle (mobile)
- [ ] Test breadcrumb navigation

## 11. Notification System

- [ ] Have admin assign a new job
- [ ] Verify operator receives notification
- [ ] Check notification bell icon shows count
- [ ] Update job status
- [ ] Verify admin receives notification
- [ ] Submit harvest report
- [ ] Verify admin receives notification

## 12. Decision Making (Advanced)

- [ ] Navigate to job detail
- [ ] Test delay decision:
  - [ ] Enter delay hours
  - [ ] Enter reason
  - [ ] Submit
  - [ ] Verify admin notified
- [ ] Test support request:
  - [ ] Select support type
  - [ ] Select urgency
  - [ ] Enter reason
  - [ ] Submit
  - [ ] Verify admin notified
- [ ] Test issue report:
  - [ ] Select issue type
  - [ ] Select severity
  - [ ] Enter details
  - [ ] Submit
  - [ ] Verify admin notified

## 13. Mobile Responsiveness

- [ ] Test on mobile device or browser dev tools
- [ ] Verify all pages responsive
- [ ] Verify touch targets large enough
- [ ] Verify text readable
- [ ] Verify forms usable
- [ ] Verify navigation works
- [ ] Verify cards stack properly

## 14. Error Handling

- [ ] Try accessing admin URLs as operator
- [ ] Verify permission denied
- [ ] Try accessing other operator's jobs
- [ ] Verify access denied
- [ ] Submit invalid harvest total (negative)
- [ ] Verify error message
- [ ] Submit empty forms
- [ ] Verify validation errors

## 15. Performance

- [ ] Check page load times
- [ ] Verify no console errors
- [ ] Verify images load properly
- [ ] Verify no broken links
- [ ] Test with slow network
- [ ] Verify graceful degradation

## 16. Cross-Browser Testing

- [ ] Test in Chrome
- [ ] Test in Firefox
- [ ] Test in Edge
- [ ] Test in Safari (if available)
- [ ] Verify consistent appearance
- [ ] Verify all features work

## 17. Admin Integration

- [ ] Login as admin
- [ ] Assign job to operator
- [ ] Verify operator receives notification
- [ ] Login as operator
- [ ] Update job status
- [ ] Login as admin
- [ ] Verify admin receives notification
- [ ] Verify status updated in admin dashboard

## 18. Data Integrity

- [ ] Submit harvest report
- [ ] Verify BUFIA share calculated correctly
- [ ] Verify member share calculated correctly
- [ ] Update job status multiple times
- [ ] Verify history tracked correctly
- [ ] Check database for data consistency

## 19. Security

- [ ] Verify operator can't access admin pages
- [ ] Verify operator can't see other operators' jobs
- [ ] Verify operator can't modify other users' data
- [ ] Verify CSRF protection works
- [ ] Verify login required for all pages

## 20. Final Checks

- [ ] All templates render without errors
- [ ] All forms submit successfully
- [ ] All links work correctly
- [ ] All images display properly
- [ ] All notifications work
- [ ] All status updates work
- [ ] All calculations correct
- [ ] No console errors
- [ ] No Python errors
- [ ] System stable

## Test Results Summary

### Passed: _____ / 100+

### Failed: _____

### Issues Found:
1. 
2. 
3. 

### Notes:


---

## Quick Test Commands

```bash
# Verify system
python test_operator_system.py

# Create operator
python create_operator.py

# Run server
python manage.py runserver

# Check diagnostics
# Use getDiagnostics tool in Kiro
```

## Test Credentials

**Operator Account:**
- Username: `operator`
- Password: `operator123`

**Admin Account:**
- Username: (your admin username)
- Password: (your admin password)

---

**Testing Date**: _____________

**Tested By**: _____________

**Status**: ⬜ Pass | ⬜ Fail | ⬜ Needs Review
