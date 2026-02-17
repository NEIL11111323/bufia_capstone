# Members Masterlist Sector-Specific Export - Implementation Complete ✅

## Overview
Updated the Members Masterlist page (`/members/masterlist/`) so that Print and Export functions respect the selected sector filter. Now admins can export or print specific sectors or all members.

---

## What Was Changed

### 1. Template Updates (`templates/users/members_masterlist.html`)

#### Added PDF Export Button
```html
<a href="{% url 'export_members_pdf' %}" id="export-pdf-btn" class="export-btn me-2">
    <i class="fas fa-file-pdf"></i> Export to PDF
</a>
```

#### Updated JavaScript
- Tracks the currently active sector tab
- Updates export links dynamically when sector changes
- Implements sector-specific printing

```javascript
let currentActiveSector = null;

function updateExportLinks() {
    if (currentActiveSector === 'all') {
        csvBtn.href = '{% url "export_members_csv" %}';
        pdfBtn.href = '{% url "export_members_pdf" %}';
    } else {
        csvBtn.href = `{% url "export_members_csv" %}?sector=${currentActiveSector}`;
        pdfBtn.href = `{% url "export_members_pdf" %}?sector=${currentActiveSector}`;
    }
}

function printCurrentTab() {
    // Hide all inactive tabs
    // Print only active tab
    // Restore all tabs
}
```

---

### 2. View Updates (`users/views.py`)

#### Updated CSV Export
```python
def export_members_csv(request):
    sector_id = request.GET.get('sector', None)
    
    # Filter by sector
    if sector_id == 'unassigned':
        applications = applications.filter(assigned_sector__isnull=True)
    elif sector_id and sector_id != 'all':
        applications = applications.filter(assigned_sector_id=int(sector_id))
    
    # Dynamic filename based on sector
    filename = f'bufia_members_{sector_name}_{date}.csv'
```

#### Added PDF Export
```python
def export_members_pdf(request):
    sector_id = request.GET.get('sector', None)
    
    # Filter members by sector
    # Render PDF template
    # Generate PDF using WeasyPrint
    # Return PDF response
```

---

### 3. New PDF Template (`templates/users/members_pdf_template.html`)

Professional PDF layout with:
- BUFIA header with logo styling
- Sector name and date
- Total member count
- Formatted table with member list
- Footer with organization info

---

### 4. URL Configuration (`users/urls.py`)

Added new route:
```python
path('members/export/pdf/', views.export_members_pdf, name='export_members_pdf'),
```

---

### 5. Dependencies (`requirements.txt`)

Added WeasyPrint for PDF generation:
```
weasyprint==60.1
```

---

## How It Works

### Scenario 1: Export All Members

1. User views "All Members" tab
2. Clicks "Export to CSV" or "Export to PDF"
3. System exports all verified members
4. Filename: `bufia_members_all_20251203.csv/pdf`

### Scenario 2: Export Specific Sector

1. User clicks on "Sector 1" tab
2. JavaScript updates export links: `?sector=1`
3. User clicks "Export to CSV" or "Export to PDF"
4. System exports only Sector 1 members
5. Filename: `bufia_members_Sector_1_20251203.csv/pdf`

### Scenario 3: Export Unassigned Members

1. User clicks on "Unassigned" tab
2. JavaScript updates export links: `?sector=unassigned`
3. User clicks export button
4. System exports only unassigned members
5. Filename: `bufia_members_unassigned_20251203.csv/pdf`

### Scenario 4: Print Specific Sector

1. User selects any sector tab
2. Clicks "Print" button
3. JavaScript hides all inactive tabs
4. Browser print dialog opens showing only active tab
5. After printing, all tabs are restored

---

## Features

### Dynamic Export Links
✅ Export links update automatically when switching tabs
✅ No page reload needed
✅ Sector parameter passed via URL query string

### Sector-Specific Printing
✅ Only prints the currently visible tab
✅ Hides other tabs during print
✅ Restores all tabs after printing
✅ Clean print output without navigation elements

### Smart Filenames
✅ Includes sector name in filename
✅ Includes date stamp
✅ Replaces spaces with underscores
✅ Examples:
- `bufia_members_all_20251203.csv`
- `bufia_members_Sector_1_20251203.pdf`
- `bufia_members_unassigned_20251203.csv`

### Professional PDF Output
✅ BUFIA branding and header
✅ Sector name clearly displayed
✅ Generation date and total count
✅ Formatted table with borders
✅ Alternating row colors for readability
✅ Footer with organization info

---

## Export Formats

### CSV Export
```
NO., NAME OF FARMER, SECTOR
1, Doe John, Sector 1
2, Smith Jane, Sector 1
3, Johnson Bob, Sector 2
```

**Features:**
- Simple 3-column format
- Easy to import into Excel/Google Sheets
- Numbered rows
- Sector information included

### PDF Export
```
┌─────────────────────────────────────────┐
│            BUFIA                        │
│      Members Masterlist                 │
│         Sector 1                        │
├─────────────────────────────────────────┤
│ Generated: December 3, 2025             │
│ Total Members: 25                       │
├─────────────────────────────────────────┤
│ NO. │ NAME OF FARMER    │ SECTOR       │
├─────┼───────────────────┼──────────────┤
│  1  │ Doe, John         │ Sector 1     │
│  2  │ Smith, Jane       │ Sector 1     │
└─────────────────────────────────────────┘
```

**Features:**
- Professional layout
- BUFIA branding
- Color-coded headers (green)
- Alternating row colors
- Page margins and formatting
- Ready for printing or archiving

---

## Technical Implementation

### JavaScript State Management
```javascript
let currentActiveSector = null;

// Track sector changes
button.addEventListener('click', function() {
    const targetId = this.getAttribute('data-bs-target');
    
    if (targetId === '#all-members-pane') {
        currentActiveSector = 'all';
    } else if (targetId.includes('unassigned')) {
        currentActiveSector = 'unassigned';
    } else {
        const match = targetId.match(/sector-(\d+)-pane/);
        if (match) {
            currentActiveSector = match[1];
        }
    }
    
    updateExportLinks();
});
```

### View Filtering Logic
```python
# Get sector parameter
sector_id = request.GET.get('sector', None)

# Filter applications
if sector_id == 'unassigned':
    applications = applications.filter(assigned_sector__isnull=True)
elif sector_id and sector_id != 'all':
    applications = applications.filter(assigned_sector_id=int(sector_id))
```

### PDF Generation
```python
from weasyprint import HTML

# Render HTML template
html_string = render_to_string('users/members_pdf_template.html', context)

# Generate PDF
html = HTML(string=html_string)
pdf_file = html.write_pdf()

# Return as response
response = HttpResponse(pdf_file, content_type='application/pdf')
```

---

## Installation

### Install WeasyPrint
```bash
pip install weasyprint==60.1
```

### Or install all requirements
```bash
pip install -r requirements.txt
```

### WeasyPrint Dependencies (Windows)
WeasyPrint requires GTK3 on Windows. If you encounter issues:

1. Download GTK3 runtime from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
2. Install GTK3
3. Restart your terminal/IDE
4. Try again

---

## Testing

### Test Scenario 1: All Members Export
1. Go to `/members/masterlist/`
2. Stay on "All Members" tab
3. Click "Export to CSV"
4. Verify file contains all members
5. Click "Export to PDF"
6. Verify PDF shows "All Sectors"

### Test Scenario 2: Sector-Specific Export
1. Click on "Sector 1" tab
2. Click "Export to CSV"
3. Verify file contains only Sector 1 members
4. Verify filename includes "Sector_1"
5. Click "Export to PDF"
6. Verify PDF shows "Sector 1" in header

### Test Scenario 3: Unassigned Export
1. Click on "Unassigned" tab
2. Click "Export to CSV"
3. Verify file contains only unassigned members
4. Verify filename includes "unassigned"

### Test Scenario 4: Print Functionality
1. Select any sector tab
2. Click "Print" button
3. Verify print preview shows only selected sector
4. Verify other tabs are hidden
5. Cancel print
6. Verify all tabs are visible again

### Test Scenario 5: Dynamic Link Updates
1. Click through different sector tabs
2. Right-click "Export to CSV" and check link
3. Verify URL includes correct sector parameter
4. Repeat for PDF export button

---

## Benefits

### For Admins
✅ **Flexible Exporting** - Export all or specific sectors
✅ **Multiple Formats** - CSV for data, PDF for printing
✅ **Smart Filenames** - Easy to identify and organize
✅ **Quick Printing** - Print only what you need
✅ **Professional Output** - PDF ready for official use

### For Organization
✅ **Sector Management** - Easy sector-specific reports
✅ **Record Keeping** - Professional PDF archives
✅ **Data Analysis** - CSV for spreadsheet analysis
✅ **Efficiency** - No manual filtering needed
✅ **Accuracy** - Automated, error-free exports

---

## Future Enhancements

### Potential Improvements
1. **Excel Export** - Native .xlsx format with formatting
2. **Email Export** - Send exports directly via email
3. **Scheduled Exports** - Automatic weekly/monthly exports
4. **Custom Fields** - Choose which columns to export
5. **Batch Export** - Export multiple sectors at once
6. **Export History** - Track who exported what and when
7. **Watermarks** - Add "CONFIDENTIAL" watermark to PDFs
8. **Digital Signatures** - Sign PDFs for authenticity

---

## Summary

The Members Masterlist now features intelligent export and print functionality that respects the selected sector:

✅ **CSV Export** - Sector-specific or all members
✅ **PDF Export** - Professional formatted documents
✅ **Smart Printing** - Print only active tab
✅ **Dynamic Links** - Auto-update based on selection
✅ **Smart Filenames** - Include sector and date
✅ **Professional Output** - Ready for official use

Admins can now efficiently export and print member lists by sector without manual filtering!

---

*Implemented: December 3, 2025*
*Page: `/members/masterlist/`*
*Files Modified: `templates/users/members_masterlist.html`, `users/views.py`, `users/urls.py`, `requirements.txt`*
*Files Created: `templates/users/members_pdf_template.html`*
