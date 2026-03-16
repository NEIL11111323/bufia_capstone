# Sector-Based Membership - Quick Start Guide

## For Developers

### Running Migrations
```bash
python manage.py migrate
```

### Accessing Features
1. **Sector Overview:** Navigate to `/sectors/overview/` or click "Sectors" in navigation
2. **Registration Dashboard:** Navigate to `/membership/registration/`
3. **Sector Reports:** Access from sector detail pages

### Key URLs
```
/sectors/overview/                          # Sector overview
/sectors/<id>/                              # Sector detail
/membership/registration/                   # Registration dashboard
/membership/registration/<id>/review/       # Review application
/reports/sectors/<id>/member-list/          # Member list report
/reports/sectors/<id>/summary/              # Summary report
/reports/sectors/comparison/                # Comparison report
```

## For Admins

### Quick Actions

**View All Sectors:**
1. Login as superuser
2. Click "Membership Management" > "Sectors"

**Review Applications:**
1. Click "Membership Management" > "Membership Registration"
2. Use filters to find applications
3. Click "Review" to see details
4. Approve or reject with reason

**Generate Reports:**
1. Go to sector detail page
2. Click "Member List Report" or "Summary Report"
3. Use export buttons for PDF/Excel

**Bulk Assign Sectors:**
1. Go to "Members" > "All Members"
2. Filter by sector if needed
3. Select members (checkboxes)
4. Choose "Assign to Sector" action
5. Select target sector and provide reason

## Testing Checklist (Priority)

### Critical Tests
- [ ] Access sector overview (should show 10 sectors)
- [ ] Access sector detail (should show members)
- [ ] Filter members by sector
- [ ] Approve a membership application
- [ ] Generate a sector report
- [ ] Export report to PDF

### Important Tests
- [ ] Bulk assign members to sector
- [ ] Search members in sector detail
- [ ] Sort members by different fields
- [ ] Test on mobile device
- [ ] Test print functionality

## Troubleshooting

**Problem:** Sectors not showing
**Solution:** Run migrations: `python manage.py migrate`

**Problem:** Cannot access admin views
**Solution:** Ensure user is superuser: `user.is_superuser = True`

**Problem:** PDF export not working
**Solution:** Enable JavaScript in browser

**Problem:** Charts not displaying
**Solution:** Check internet connection (CDN libraries)

## File Locations

### Views
- `users/views.py` - Sector management views
- `reports/views.py` - Report generation views

### Templates
- `templates/users/sector_overview.html`
- `templates/users/sector_detail.html`
- `templates/users/registration_dashboard.html`
- `templates/reports/sector_member_list.html`
- `templates/reports/sector_summary.html`
- `templates/reports/sector_comparison.html`

### URLs
- `users/urls.py` - Sector and membership URLs
- `reports/urls.py` - Report URLs

## Support

For detailed documentation, see:
- `IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `PHASE1_IMPLEMENTATION_SUMMARY.md` through `PHASE6_IMPLEMENTATION_SUMMARY.md`
- `.kiro/specs/sector-membership-navigation/` - Original specifications
