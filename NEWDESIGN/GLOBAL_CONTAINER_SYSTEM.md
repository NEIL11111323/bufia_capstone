# Global Container & Card System

## Overview
This document outlines the standardized container and card system implemented across all pages of the BUFIA application. All containers, cards, and UI elements now use consistent sizing, border radius, shadows, and styling that matches the dashboard design.

## Core Design Principles

### Border Radius Standards
- **Large Cards/Containers**: `1rem` (16px) - Main cards, sections, modals
- **Medium Elements**: `0.75rem` (12px) - Dropdowns, popovers
- **Small Elements**: `0.5rem` (8px) - Buttons, form inputs, badges
- **Pills**: `50rem` - Badge pills, rounded buttons

### Shadow System
- **Base Shadow**: `0 0.5rem 1rem rgba(0, 0, 0, 0.08)` - Default cards
- **Hover Shadow**: `0 1rem 2rem rgba(0, 0, 0, 0.12)` - Elevated state
- **Light Shadow**: `0 0.25rem 0.5rem rgba(0, 0, 0, 0.05)` - Subtle elements
- **Modal Shadow**: `0 1rem 3rem rgba(0, 0, 0, 0.175)` - Overlays

### Spacing Standards
- **Card Padding**: `1.5rem` (24px) - Standard card body
- **Large Padding**: `2rem` (32px) - Section containers
- **Compact Padding**: `1.25rem` (20px) - Mobile/tight spaces
- **Card Header/Footer**: `1.25rem 1.5rem` - Vertical/Horizontal

## Component Styling

### 1. Cards

#### Base Card
```html
<div class="card">
    <div class="card-header">
        <h5>Card Title</h5>
    </div>
    <div class="card-body">
        Card content goes here
    </div>
    <div class="card-footer">
        Footer content
    </div>
</div>
```

**Styling:**
- Border radius: `1rem`
- Shadow: `0 0.5rem 1rem rgba(0, 0, 0, 0.08)`
- No border
- White background
- Hover: Elevated shadow

#### Stat Cards
```html
<div class="stat-card">
    <div class="d-flex align-items-center">
        <div class="flex-shrink-0">
            <i class="fas fa-icon fa-2x"></i>
        </div>
        <div class="flex-grow-1">
            <h6 class="text-muted mb-1">Label</h6>
            <h3 class="mb-0">Value</h3>
        </div>
    </div>
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `1.5rem`
- Icon box: `60x60px` with colored background
- Hover: Lifts up 5px

### 2. Containers

#### Section Container
```html
<div class="section-container">
    <h3>Section Title</h3>
    <p>Section content...</p>
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `2rem`
- Shadow: Base shadow
- Margin bottom: `2rem`

#### Content Card
```html
<div class="content-card">
    Content goes here
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `1.5rem`
- Shadow: Base shadow
- Margin bottom: `1.5rem`

### 3. List Items

#### Rental/Request Items
```html
<div class="rental-item">
    <div class="row">
        <!-- Item content -->
    </div>
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `1.5rem`
- Shadow: Base shadow
- Hover: Lifts up 2px with enhanced shadow
- Optional: Left border for status indication

### 4. Forms

#### Form Container
```html
<div class="form-container">
    <form>
        <div class="mb-3">
            <label class="form-label">Label</label>
            <input type="text" class="form-control">
        </div>
    </form>
</div>
```

**Form Control Styling:**
- Border radius: `0.5rem`
- Border: `1px solid #e9ecef`
- Focus: Bufia green border with shadow
- Padding: `0.625rem 0.75rem`

### 5. Modals

#### Modal Structure
```html
<div class="modal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Modal Title</h5>
            </div>
            <div class="modal-body">
                Content
            </div>
            <div class="modal-footer">
                Buttons
            </div>
        </div>
    </div>
</div>
```

**Styling:**
- Border radius: `1rem`
- Shadow: `0 1rem 3rem rgba(0, 0, 0, 0.175)`
- No border
- Header/footer with subtle background

### 6. Tables

#### Table Container
```html
<div class="table-card">
    <div class="table-responsive">
        <table class="table">
            <!-- Table content -->
        </table>
    </div>
</div>
```

**Styling:**
- Border radius: `1rem`
- Overflow: hidden
- Shadow: Base shadow
- No internal borders on container

### 7. Alerts

#### Alert Box
```html
<div class="alert alert-success">
    <i class="fas fa-check-circle me-2"></i>
    Success message
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `1.25rem 1.5rem`
- No border
- Light shadow
- Margin bottom: `1.5rem`

### 8. Empty States

#### Empty State
```html
<div class="empty-state">
    <i class="fas fa-inbox"></i>
    <p>No items found</p>
    <button class="btn btn-primary">Add New</button>
</div>
```

**Styling:**
- Border radius: `1rem`
- Padding: `3rem 2rem`
- Shadow: Base shadow
- Centered text
- Large icon (4rem) with opacity

### 9. Badges

#### Badge Styles
```html
<span class="badge bg-success">Active</span>
<span class="badge badge-pill bg-primary">New</span>
```

**Styling:**
- Border radius: `0.5rem` (standard)
- Border radius: `50rem` (pill variant)
- Padding: `0.4rem 0.75rem`
- Font size: `0.85rem`
- Font weight: 600

### 10. Pagination

#### Pagination
```html
<nav>
    <ul class="pagination">
        <li class="page-item"><a class="page-link" href="#">1</a></li>
        <li class="page-item active"><a class="page-link" href="#">2</a></li>
        <li class="page-item"><a class="page-link" href="#">3</a></li>
    </ul>
</nav>
```

**Styling:**
- Border radius: `0.5rem` per item
- Margin: `0.25rem` between items
- Bufia green for active state
- Hover: Light green background

## Class Reference

### Card Classes
- `.card` - Base card
- `.stat-card` / `.stat-box` - Dashboard-style stat cards
- `.info-card` - Information cards
- `.content-card` - Content containers
- `.data-card` - Data display cards
- `.list-card` - List containers
- `.detail-card` - Detail view cards
- `.form-card` - Form containers

### Container Classes
- `.section-container` - Large section wrapper
- `.page-section` - Page section wrapper
- `.form-container` - Form wrapper
- `.form-wrapper` - Alternative form wrapper

### Filter & Search
- `.filter-card` - Filter controls container
- `.search-card` - Search controls container

### Table Classes
- `.table-card` - Table wrapper
- `.data-table-container` - Data table wrapper

### List Item Classes
- `.list-item` - Generic list item
- `.data-item` - Data list item
- `.rental-item` - Rental list item
- `.request-item` - Request list item

### Empty State Classes
- `.empty-state` - Empty state container
- `.no-data-state` - No data container

### Utility Classes
- `.rounded-card` - Force 1rem border radius
- `.rounded-lg` - 1rem border radius
- `.rounded-md` - 0.75rem border radius
- `.rounded-sm` - 0.5rem border radius
- `.shadow-card` - Apply base shadow
- `.shadow-card-hover` - Apply hover effect

## Usage Examples

### Dashboard Stat Cards
```html
<div class="row">
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex align-items-center">
                <div class="flex-shrink-0 bg-primary bg-opacity-25">
                    <i class="fas fa-users fa-2x text-primary"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="text-muted mb-1">Total Users</h6>
                    <h3 class="mb-0">150</h3>
                </div>
            </div>
        </div>
    </div>
</div>
```

### Content Section
```html
<div class="section-container">
    <h3>Recent Activity</h3>
    <div class="list-item">
        <p>Activity item 1</p>
    </div>
    <div class="list-item">
        <p>Activity item 2</p>
    </div>
</div>
```

### Form Page
```html
<div class="form-container">
    <h3 class="mb-4">Create New Rental</h3>
    <form>
        <div class="mb-3">
            <label class="form-label">Machine</label>
            <select class="form-select">
                <option>Select machine...</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary">Submit</button>
    </form>
</div>
```

### Data Table
```html
<div class="table-card">
    <div class="card-header">
        <h5>Rental List</h5>
    </div>
    <div class="table-responsive">
        <table class="table">
            <thead>
                <tr>
                    <th>Machine</th>
                    <th>User</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <!-- Table rows -->
            </tbody>
        </table>
    </div>
</div>
```

## Responsive Behavior

### Mobile (< 768px)
- Card padding reduced to `1.25rem`
- Section padding reduced to `1.25rem`
- Empty state padding reduced to `2rem 1.25rem`
- Stat cards maintain structure but with tighter spacing

### Tablet (768px - 992px)
- Standard padding maintained
- Grid layouts adjust to fewer columns
- Cards stack vertically when needed

### Desktop (> 992px)
- Full padding and spacing
- Multi-column layouts
- Hover effects fully enabled

## Color Integration

All containers use the Bufia brand color system:
- **Primary Green**: `#047857` - Active states, borders
- **Primary Dark**: `#065F46` - Hover states
- **Primary Light**: `#D1FAE5` - Backgrounds, hover backgrounds
- **Neutral Grays**: `#f8f9fa`, `#e9ecef` - Backgrounds, borders

## Benefits

1. **Consistency**: All pages look cohesive and professional
2. **Maintainability**: Single source of truth for styling
3. **Scalability**: Easy to add new components with consistent styling
4. **Accessibility**: Proper contrast and focus states
5. **Responsive**: Works seamlessly across all device sizes
6. **Modern**: Clean, contemporary design matching current trends
7. **Brand Identity**: Consistent use of Bufia colors and styling

## Implementation

The global container system is implemented in:
- `static/css/global-container-system.css` - Main system file
- Loaded in `templates/base.html` after typography system
- Applies to all pages automatically
- Overrides Bootstrap defaults where needed

## Migration Guide

To update existing pages to use the new system:

1. Replace old card classes with `.card`
2. Use `.stat-card` for dashboard-style statistics
3. Wrap content in `.section-container` or `.content-card`
4. Use `.list-item` for list entries
5. Apply `.empty-state` for no-data scenarios
6. Remove custom border-radius and shadow styles
7. Let the global system handle consistency

The system is designed to work with existing Bootstrap markup while providing enhanced, consistent styling across the entire application.
