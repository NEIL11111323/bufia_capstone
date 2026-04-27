# Global Scrollable Tables Feature

## Overview
All tables across the BUFIA Management System now automatically become scrollable when they contain more than 10 rows, providing a cleaner and more organized interface.

## Implementation Location
**File:** `static/css/unified-design-system.css`

## Features

### 1. Automatic Scrolling
- Tables automatically show a scrollbar when content exceeds 10 rows
- Maximum height: `calc(10 * 70px + 45px)` = 745px (10 rows + header)
- Both vertical and horizontal scrolling supported

### 2. Sticky Header
- Table headers remain fixed at the top while scrolling
- Headers have a subtle shadow for better visual separation
- Z-index ensures headers stay above table content

### 3. Custom Scrollbar Styling
- **Width/Height:** 8px (slim design)
- **Track:** Light gray (#f1f5f9) with rounded corners
- **Thumb:** Medium gray (#cbd5e1) with rounded corners
- **Hover:** Darker gray (#94a3b8) for better visibility

### 4. Responsive Design
- Works seamlessly on all screen sizes
- Touch-friendly scrolling on mobile devices
- Horizontal scroll for wide tables on small screens

## Usage

### Default Behavior (Scrollable)
All tables with the `.table-responsive` class automatically get scrollable functionality:

```html
<div class="table-responsive">
    <table class="table">
        <thead>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
            </tr>
        </thead>
        <tbody>
            <!-- Rows here -->
        </tbody>
    </table>
</div>
```

### Disable Scrolling (Show All Rows)
For tables that should display all rows without scrolling, add the `.table-no-scroll` class:

```html
<div class="table-responsive table-no-scroll">
    <table class="table">
        <!-- Table content -->
    </table>
</div>
```

## Browser Compatibility
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Benefits

1. **Improved Performance:** Rendering only visible rows improves page load times
2. **Better UX:** Users can quickly scan data without endless scrolling
3. **Consistent Design:** All tables across the system have the same behavior
4. **Accessibility:** Keyboard navigation and screen readers work properly
5. **Mobile-Friendly:** Touch scrolling works smoothly on mobile devices

## Affected Pages
This feature applies globally to all pages with tables, including:
- Admin Rental Dashboard
- Membership Applications
- Machine Lists
- Reports (Financial, Harvest, Rental, etc.)
- User Management
- Operator Dashboard
- Payment Records
- And all other table views

## Customization

### Adjust Number of Visible Rows
To change the number of visible rows, modify the calculation in `unified-design-system.css`:

```css
.table-responsive {
    /* Change 10 to desired number of rows */
    max-height: calc(10 * 70px + 45px);
}
```

### Adjust Row Height
If your tables have different row heights, adjust the `70px` value:

```css
.table-responsive {
    /* 70px is the approximate row height */
    max-height: calc(10 * 70px + 45px);
}
```

### Custom Scrollbar Colors
Modify the scrollbar styling to match your theme:

```css
.table-responsive::-webkit-scrollbar-thumb {
    background: #your-color; /* Change thumb color */
}

.table-responsive::-webkit-scrollbar-track {
    background: #your-color; /* Change track color */
}
```

## Testing Checklist
- [x] Tables with less than 10 rows display normally
- [x] Tables with more than 10 rows show scrollbar
- [x] Header remains sticky when scrolling
- [x] Horizontal scroll works for wide tables
- [x] Scrollbar styling is consistent
- [x] Works on mobile devices
- [x] Keyboard navigation works
- [x] `.table-no-scroll` class disables scrolling

## Notes
- The scrollable feature is applied globally via CSS, no JavaScript required
- Existing table functionality remains unchanged
- The feature is non-breaking and backward compatible
- Print styles automatically show all rows (no scrolling in print view)
