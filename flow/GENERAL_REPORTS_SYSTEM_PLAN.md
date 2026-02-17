# General Reports System - Implementation Plan

## Overview
Create a comprehensive reporting system for BUFIA with monthly, weekly, and yearly reports that can be viewed online, printed, and exported as PDF files. Only accessible by admin users.

## Features

### 1. Report Types

#### Weekly Report
- Total rentals this week
- Total appointments this week
- Revenue generated
- Active members
- Pending approvals
- Machine utilization

#### Monthly Report
- Total rentals this month
- Total appointments this month
- Revenue breakdown
- Member activity statistics
- Payment statistics
- Machine usage by type
- Top performing machines
- Comparison with previous month

#### Yearly Report
- Annual revenue summary
- Total rentals/appointments
- Growth trends (month by month)
- Member statistics
- Seasonal patterns
- Machine performance analysis
- Revenue by machine type
- Year-over-year comparison

### 2. Export Formats
- **PDF** - Professional formatted reports for printing
- **Excel/CSV** - Data export for further analysis
- **Print-friendly HTML** - Direct browser printing

### 3. Access Control
- Only admin users (superuser) can access
- Button added to profile page
- Separate reports dashboard

## Implementation Steps

### Phase 1: Backend (reports app)
1. Create `reports` app
2. Create report generation functions
3. Create views for each report type
4. Add URL patterns
5. Create PDF generation utility

### Phase 2: Frontend
1. Create reports dashboard template
2. Create individual report templates
3. Add PDF styling
4. Add print CSS
5. Create charts/graphs (optional)

### Phase 3: Integration
1. Add "General Reports" button to admin profile
2. Add navigation in reports section
3. Test all report types
4. Test PDF generation
5. Test printing

### Phase 4: Enhancements (Optional)
1. Email reports automatically
2. Schedule report generation
3. Save report history
4. Add custom date ranges
5. Add filtering options

## File Structure

```
reports/
├── __init__.py
├── admin.py
├── apps.py
├── models.py (optional - for saving report history)
├── views.py
├── urls.py
├── utils.py (report generation logic)
├── pdf_generator.py (PDF creation)
└── templates/
    └── reports/
        ├── dashboard.html
        ├── weekly_report.html
        ├── monthly_report.html
        ├── yearly_report.html
        └── pdf/
            ├── weekly_pdf.html
            ├── monthly_pdf.html
            └── yearly_pdf.html
```

## Data to Include

### Rentals Data
- Total count
- By status (pending, approved, completed)
- By machine type
- Revenue generated
- Average rental duration

### Appointments Data
- Total count
- By status (pending, approved, completed, cancelled)
- By rice mill
- Revenue generated
- Busiest days/times

### Irrigation Requests
- Total count
- By status
- Water usage statistics
- Revenue generated

### Members Data
- Total active members
- New members (period)
- Member activity
- Payment statistics

### Financial Data
- Total revenue
- Revenue by service type
- Payment methods
- Pending payments
- Completed payments

## Technologies

### PDF Generation
- **ReportLab** - Python PDF library
- **WeasyPrint** - HTML to PDF (alternative)
- **xhtml2pdf** - HTML to PDF (simpler)

### Excel Export
- **openpyxl** - Excel file generation
- **pandas** - Data manipulation and export

### Charts (Optional)
- **Chart.js** - JavaScript charts
- **Matplotlib** - Python charts in PDF
- **Plotly** - Interactive charts

## User Interface

### Reports Dashboard
```
┌─────────────────────────────────────────┐
│  📊 General Reports Dashboard           │
├─────────────────────────────────────────┤
│                                         │
│  Select Report Type:                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Weekly  │ │ Monthly │ │ Yearly  │  │
│  │ Report  │ │ Report  │ │ Report  │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│                                         │
│  Quick Actions:                         │
│  [View] [Download PDF] [Export Excel]  │
│                                         │
│  Recent Reports:                        │
│  • Monthly Report - November 2025       │
│  • Weekly Report - Week 48              │
│  • Yearly Report - 2024                 │
└─────────────────────────────────────────┘
```

### Profile Integration
```
Admin Profile Page:
┌─────────────────────────────────────────┐
│  Admin Dashboard                        │
├─────────────────────────────────────────┤
│  [Manage Users]                         │
│  [Manage Machines]                      │
│  [📊 General Reports] ← NEW BUTTON     │
│  [System Settings]                      │
└─────────────────────────────────────────┘
```

## Security
- `@login_required` decorator
- `@user_passes_test(lambda u: u.is_superuser)` decorator
- Check permissions in templates
- Secure PDF file storage

## Next Steps

Would you like me to:
1. **Start implementing now** - Begin with Phase 1
2. **Review this plan** - Make any changes first
3. **See a prototype** - Create a simple version first

Let me know and I'll proceed with the implementation!
