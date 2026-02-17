# Split-Screen Rental Layout

## Overview
Updated the Equipment Rentals page to display Upcoming Rentals and Rental History side-by-side in a split-screen layout, allowing users to see both sections simultaneously.

## Layout Design

### Split-Screen Structure

```
┌─────────────────────────────────────────────────────────┐
│                    Statistics Cards                      │
│  [Ongoing] [Upcoming] [Pending] [Past]                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Pending Rentals (Full Width)                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Ongoing Rentals (Full Width)                │
└─────────────────────────────────────────────────────────┘

┌──────────────────────────┬──────────────────────────────┐
│   Upcoming Rentals       │    Rental History            │
│   (Left Column)          │    (Right Column)            │
│                          │                              │
│   [Scrollable]           │    [Scrollable]              │
│   Max Height: 600px      │    Max Height: 600px         │
│                          │                              │
└──────────────────────────┴──────────────────────────────┘
```

## Features

### 1. Side-by-Side Layout
- **Left Column**: Upcoming Rentals (scheduled future bookings)
- **Right Column**: Rental History (past completed rentals)
- **Equal Width**: Each column takes 50% of the screen width
- **Responsive**: Stacks vertically on mobile devices

### 2. Scrollable Sections
- **Max Height**: 600px for each column
- **Independent Scrolling**: Each column scrolls separately
- **Custom Scrollbar**: Green-themed scrollbar matching BUFIA design
- **Smooth Scrolling**: Optimized for better user experience

### 3. Compact Card Design
Each rental card now displays:
- Machine name with icon
- Date range and duration badge
- Status information (days until start / days since completion)
- Rental cost
- Compact "View" button

### 4. Custom Scrollbar Styling

```css
.scrollable-section::-webkit-scrollbar {
    width: 8px;
}

.scrollable-section::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}

.scrollable-section::-webkit-scrollbar-thumb {
    background: #019d66;  /* BUFIA green */
    border-radius: 10px;
}

.scrollable-section::-webkit-scrollbar-thumb:hover {
    background: #017a4f;  /* Darker green on hover */
}
```

## Section Organization

### Full-Width Sections (Top)
1. **Statistics Dashboard** - 4 cards showing counts
2. **Pending Rentals** - Awaiting approval (yellow highlight)
3. **Ongoing Rentals** - Currently active (green highlight)

### Split-Screen Sections (Bottom)
4. **Upcoming Rentals** (Left) - Approved future bookings (blue highlight)
5. **Rental History** (Right) - Completed rentals (gray, shows last 10)

## Responsive Behavior

### Desktop (> 992px)
- Side-by-side layout
- Each column: 50% width
- Max height: 600px
- Independent scrolling

### Tablet (768px - 991px)
- Side-by-side layout maintained
- Reduced max height: 400px
- Smaller cards

### Mobile (< 768px)
- Stacked vertically
- Full width for each section
- Max height: 400px
- Margin between sections

## Benefits

✅ **Better Overview**: See both upcoming and past rentals at once
✅ **Space Efficient**: Utilizes screen width effectively
✅ **Easy Comparison**: Compare future bookings with past rentals
✅ **Reduced Scrolling**: Split view reduces overall page scrolling
✅ **Clean Design**: Organized, modern layout
✅ **Responsive**: Works on all screen sizes
✅ **Custom Scrollbars**: Branded green scrollbars
✅ **Independent Navigation**: Scroll each section separately

## User Experience

### Viewing Upcoming Rentals
- Scroll left column to see all scheduled bookings
- See days until each rental starts
- View rental costs at a glance
- Quick access to details

### Viewing Rental History
- Scroll right column to see past rentals
- See completion dates and status
- Review past rental patterns
- Access historical records

### Empty States
- If no upcoming rentals: Shows "Book Equipment" button
- If no history: Shows friendly empty state message
- Maintains layout structure even when empty

## Visual Hierarchy

1. **Top Priority**: Statistics (always visible)
2. **High Priority**: Pending & Ongoing (full width, immediate attention)
3. **Medium Priority**: Upcoming & History (split view, reference information)
4. **Action**: "Book New Equipment" button at bottom

## Testing

1. **Desktop View**:
   - Verify columns are side-by-side
   - Check scrolling works independently
   - Verify max height is 600px

2. **Tablet View**:
   - Verify layout maintains split
   - Check reduced height (400px)

3. **Mobile View**:
   - Verify sections stack vertically
   - Check full-width display
   - Verify spacing between sections

4. **Scrolling**:
   - Test custom scrollbar appearance
   - Verify smooth scrolling
   - Check hover effects on scrollbar

5. **Content**:
   - Test with many rentals (scrolling needed)
   - Test with few rentals (no scrolling)
   - Test empty states

## Result

The Equipment Rentals page now features a modern split-screen layout that allows users to simultaneously view their upcoming bookings and rental history, making it easier to plan future rentals and review past activity!
