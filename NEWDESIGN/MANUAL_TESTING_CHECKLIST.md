# BUFIA System - Manual Testing Checklist

## Complete Feature Testing Guide
**Test Date:** _____________  
**Tester:** _____________  
**Browser:** _____________

---

## 🔐 AUTHENTICATION & REGISTRATION

### Public Pages (Not Logged In)
- [ ] **Home Page** (`/`)
  - [ ] Page loads without errors
  - [ ] Login button visible in navbar
  - [ ] No sidebar visible (only for authenticated users)
  
- [ ] **Login Page** (`/accounts/login/`)
  - [ ] Login form displays correctly
  - [ ] Username field works
  - [ ] Password field works
  - [ ] "Remember me" checkbox (if present)
  - [ ] Login button works
  - [ ] Error messages show for invalid credentials
  - [ ] Redirect to dashboard after successful login
  
- [ ] **Registration Page** (`/accounts/signup/`)
  - [ ] Registration form displays
  - [ ] All required fields present
  - [ ] Password confirmation works
  - [ ] Terms and conditions checkbox (if present)
  - [ ] Registration creates new user
  - [ ] Auto-login after registration
  - [ ] Redirect to appropriate page

---

## 👤 REGULAR USER FEATURES

### Dashboard & Profile
- [ ] **Dashboard** (`/dashboard/`)
  - [ ] Sidebar navigation visible
  - [ ] Dashboard loads without errors
  - [ ] Statistics cards display correctly
  - [ ] Charts/graphs render (if present)
  - [ ] Recent activity shows
  - [ ] All data displays correctly
  
- [ ] **Profile Page** (`/profile/`)
  - [ ] Profile information displays
  - [ ] Profile photo/avatar shows
  - [ ] Edit profile button works
  - [ ] Can update profile information
  - [ ] Changes save successfully
  - [ ] Verification status shows correctly
  
- [ ] **Account Settings** (`/accounts/email/`)
  - [ ] Email settings page loads
  - [ ] Can change email
  - [ ] Email verification works (if enabled)
  - [ ] Settings save correctly

### Equipment & Scheduling
- [ ] **Machines List** (`/machines/`)
  - [ ] All machines display
  - [ ] Machine cards/list items show correctly
  - [ ] Machine images load
  - [ ] Machine details visible
  - [ ] Can view machine details
  - [ ] Availability status shows
  - [ ] Can request rental (if applicable)
  
- [ ] **Rice Mill Appointments** (`/machines/rice-mill-appointments/`)
  - [ ] Appointments list displays
  - [ ] Can create new appointment
  - [ ] Calendar/date picker works
  - [ ] Time slot selection works
  - [ ] Appointment confirmation works
  - [ ] Can view appointment details
  - [ ] Can cancel appointment (if allowed)
  
- [ ] **Equipment Rentals** (`/machines/rentals/`)
  - [ ] Rental list displays
  - [ ] Can create new rental request
  - [ ] Rental form works correctly
  - [ ] Date range picker works
  - [ ] Equipment selection works
  - [ ] Rental status shows correctly
  - [ ] Can view rental details
  - [ ] Can cancel rental (if allowed)
  - [ ] Payment integration works (if enabled)

### Services
- [ ] **Water Irrigation** (`/irrigation/requests/`)
  - [ ] Irrigation requests list displays
  - [ ] Can create new irrigation request
  - [ ] Request form works correctly
  - [ ] Date/time selection works
  - [ ] Hectares input works
  - [ ] Request status shows
  - [ ] Can view request details
  - [ ] Can cancel request (if allowed)

### Notifications
- [ ] **Notifications Dropdown**
  - [ ] Notification bell icon shows
  - [ ] Unread count badge displays
  - [ ] Dropdown opens correctly
  - [ ] Recent notifications show
  - [ ] Can click to view notification
  - [ ] "View All" link works
  
- [ ] **All Notifications** (`/notifications/user-notifications/`)
  - [ ] All notifications list displays
  - [ ] Notifications grouped/sorted correctly
  - [ ] Can mark as read
  - [ ] Can delete notifications
  - [ ] Pagination works (if present)

---

## 👨‍💼 ADMIN/SUPERUSER FEATURES

### User Management
- [ ] **Members List** (`/users/`)
  - [ ] All users display
  - [ ] User information shows correctly
  - [ ] Search/filter works
  - [ ] Can view user details
  - [ ] Can edit user information
  - [ ] Can verify users
  - [ ] Can reject verification
  - [ ] Can delete users
  - [ ] Export to CSV works
  - [ ] Export to PDF works
  
- [ ] **Verification Requests**
  - [ ] Pending verifications show
  - [ ] Can approve verification
  - [ ] Can reject verification
  - [ ] Verification status updates correctly

### Equipment Management
- [ ] **Maintenance Records** (`/machines/maintenance/`)
  - [ ] Maintenance list displays
  - [ ] Can create maintenance record
  - [ ] Can edit maintenance record
  - [ ] Can delete maintenance record
  - [ ] Maintenance history shows
  - [ ] Can assign maintenance to machine

### Notifications Management
- [ ] **Send Notifications** (`/notifications/send/`)
  - [ ] Send notification form displays
  - [ ] Can select recipients
  - [ ] User autocomplete works
  - [ ] Can select notification type
  - [ ] Message field works
  - [ ] Can send to all users
  - [ ] Can send to specific users
  - [ ] Notification sends successfully
  - [ ] Recipients receive notification

### Reports & Analytics
- [ ] **User Activity Report** (`/reports/user-activity/`)
  - [ ] Report displays correctly
  - [ ] Date range filter works
  - [ ] User filter works
  - [ ] Data displays accurately
  - [ ] Export functionality works
  
- [ ] **Machine Usage Report** (`/reports/machine-usage/`)
  - [ ] Report displays correctly
  - [ ] Machine filter works
  - [ ] Date range filter works
  - [ ] Usage statistics show
  - [ ] Export functionality works
  
- [ ] **Rice Mill Scheduling Report** (`/reports/rice-mill-scheduling/`)
  - [ ] Report displays correctly
  - [ ] Scheduling data shows
  - [ ] Date range filter works
  - [ ] Export functionality works
  
- [ ] **General Reports** (`/general-reports/`)
  - [ ] Dashboard displays
  - [ ] All report types accessible
  - [ ] Charts/graphs render
  - [ ] Data is accurate

### Activity Logs
- [ ] **Activity Logs** (`/activity-logs/`)
  - [ ] Activity log list displays
  - [ ] All activities logged
  - [ ] User filter works
  - [ ] Date filter works
  - [ ] Action filter works
  - [ ] Pagination works
  - [ ] Can view log details

### Django Admin
- [ ] **Admin Panel** (`/admin/`)
  - [ ] Admin panel accessible
  - [ ] All models visible
  - [ ] Can add records
  - [ ] Can edit records
  - [ ] Can delete records
  - [ ] Search works
  - [ ] Filters work

---

## 🎨 SIDEBAR NAVIGATION

### Sidebar Functionality
- [ ] **Sidebar Display**
  - [ ] Sidebar shows on all authenticated pages
  - [ ] Sidebar has correct width
  - [ ] All menu items visible
  - [ ] Icons display correctly
  - [ ] Text labels readable
  
- [ ] **Sidebar Collapse/Expand**
  - [ ] Toggle button works
  - [ ] Sidebar collapses to icon-only view
  - [ ] Sidebar expands back to full view
  - [ ] State persists across pages
  - [ ] Smooth animation
  
- [ ] **Active Page Highlighting**
  - [ ] Current page highlighted in sidebar
  - [ ] Active state styling correct
  - [ ] Indicator shows on active item
  
- [ ] **Dropdown Menus**
  - [ ] Reports dropdown works
  - [ ] Dropdown expands/collapses
  - [ ] Dropdown items clickable
  - [ ] Dropdown arrow rotates
  
- [ ] **Mobile Responsive**
  - [ ] Sidebar hidden on mobile by default
  - [ ] Hamburger menu shows on mobile
  - [ ] Sidebar slides in from left
  - [ ] Overlay appears when sidebar open
  - [ ] Can close sidebar by clicking overlay
  - [ ] Can close sidebar by clicking link

---

## 🎨 TOP NAVIGATION BAR

### Top Bar Elements
- [ ] **Brand Logo**
  - [ ] Logo displays correctly
  - [ ] Logo links to home
  - [ ] Hover effect works
  
- [ ] **Search Box** (Desktop only)
  - [ ] Search box visible
  - [ ] Can type in search box
  - [ ] Search functionality works
  
- [ ] **Notifications Bell**
  - [ ] Bell icon visible
  - [ ] Badge shows unread count
  - [ ] Dropdown opens on click
  - [ ] Notifications display correctly
  
- [ ] **User Menu**
  - [ ] User avatar/initial shows
  - [ ] User name displays
  - [ ] User role displays
  - [ ] Dropdown opens on click
  - [ ] Profile link works
  - [ ] Settings link works
  - [ ] Logout works correctly

---

## 📱 RESPONSIVE DESIGN

### Desktop (1920x1080)
- [ ] Layout looks good
- [ ] Sidebar fully visible
- [ ] All elements properly sized
- [ ] No horizontal scroll
- [ ] No overlapping elements

### Laptop (1366x768)
- [ ] Layout adapts correctly
- [ ] Sidebar still functional
- [ ] Content readable
- [ ] No layout issues

### Tablet (768x1024)
- [ ] Sidebar becomes mobile menu
- [ ] Touch interactions work
- [ ] Content stacks properly
- [ ] Navigation accessible

### Mobile (375x667)
- [ ] Sidebar hidden by default
- [ ] Hamburger menu works
- [ ] Content fully responsive
- [ ] Touch targets adequate size
- [ ] No horizontal scroll
- [ ] Forms usable on mobile

---

## 🔒 SECURITY & PERMISSIONS

### Access Control
- [ ] **Anonymous Users**
  - [ ] Cannot access dashboard
  - [ ] Redirected to login
  - [ ] Cannot access protected pages
  
- [ ] **Regular Users**
  - [ ] Can access own dashboard
  - [ ] Cannot access admin features
  - [ ] Cannot access other users' data
  - [ ] Cannot access maintenance records
  
- [ ] **Admin Users**
  - [ ] Can access all features
  - [ ] Can manage users
  - [ ] Can access reports
  - [ ] Can send notifications
  - [ ] Can access admin panel

---

## ⚡ PERFORMANCE

### Page Load Times
- [ ] Home page loads < 2 seconds
- [ ] Dashboard loads < 3 seconds
- [ ] List pages load < 2 seconds
- [ ] No excessive loading spinners
- [ ] Images load progressively

### Interactions
- [ ] Sidebar toggle is instant
- [ ] Dropdown menus open smoothly
- [ ] Form submissions responsive
- [ ] No lag in navigation
- [ ] Smooth scrolling

---

## 🐛 ERROR HANDLING

### Error Pages
- [ ] 404 page displays correctly
- [ ] 403 page displays correctly
- [ ] 500 page displays correctly (test in production mode)
- [ ] Error messages are user-friendly

### Form Validation
- [ ] Required fields validated
- [ ] Error messages display clearly
- [ ] Success messages show
- [ ] Form doesn't submit with errors
- [ ] Validation is client and server-side

---

## 🎯 BROWSER COMPATIBILITY

Test in multiple browsers:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (if available)
- [ ] Mobile browsers (Chrome Mobile, Safari iOS)

---

## 📝 NOTES & ISSUES FOUND

### Critical Issues
```
(List any critical bugs that prevent core functionality)
```

### Minor Issues
```
(List any minor bugs or UI issues)
```

### Suggestions
```
(List any improvements or enhancements)
```

---

## ✅ FINAL SIGN-OFF

- [ ] All critical features working
- [ ] No blocking bugs found
- [ ] Design looks good across devices
- [ ] Performance acceptable
- [ ] Ready for production

**Tested By:** _____________  
**Date:** _____________  
**Signature:** _____________

---

**Testing Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Issues Found
