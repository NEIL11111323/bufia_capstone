# Typography & Button Standardization Guide

## Overview
This document outlines the standardized typography and button system implemented across the BUFIA application, ensuring consistent text styles and button sizes that match the dashboard design.

## Typography System

### Font Family
- **Primary Font**: Inter (Google Fonts)
- **Fallback**: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif

### Font Size Scale

| Size Name | CSS Variable | Value | Usage |
|-----------|-------------|-------|-------|
| Extra Small | `--font-size-xs` | 0.75rem (12px) | Small labels, badges, timestamps |
| Small | `--font-size-sm` | 0.85rem (13.6px) | Table headers, secondary text, form labels |
| Base | `--font-size-base` | 0.9rem (14.4px) | Body text, form inputs, table cells |
| Medium | `--font-size-md` | 0.95rem (15.2px) | Links, buttons, subtext |
| Large | `--font-size-lg` | 1.1rem (17.6px) | Subheadings, h4 |
| Extra Large | `--font-size-xl` | 1.25rem (20px) | Card titles, h3 |
| 2X Large | `--font-size-2xl` | 1.5rem (24px) | Section headers, h2 |
| 3X Large | `--font-size-3xl` | 1.75rem (28px) | Page titles, h1, dashboard title |
| 4X Large | `--font-size-4xl` | 2.5rem (40px) | Dashboard statistics |

### Font Weights

| Weight Name | CSS Variable | Value | Usage |
|-------------|-------------|-------|-------|
| Normal | `--font-normal` | 400 | Body text, paragraphs |
| Medium | `--font-medium` | 500 | Links, emphasized text |
| Semibold | `--font-semibold` | 600 | Labels, table headers, h4-h6 |
| Bold | `--font-bold` | 700 | Headings h1-h3, card titles |
| Extra Bold | `--font-extrabold` | 800 | Special emphasis |

### Line Heights

| Name | CSS Variable | Value | Usage |
|------|-------------|-------|-------|
| Tight | `--line-height-tight` | 1.2 | Headings, titles |
| Normal | `--line-height-normal` | 1.5 | Labels, small text |
| Relaxed | `--line-height-relaxed` | 1.6 | Body text, paragraphs |

### Letter Spacing

| Name | CSS Variable | Value | Usage |
|------|-------------|-------|-------|
| Tight | `--letter-spacing-tight` | -0.025em | Large headings |
| Normal | `--letter-spacing-normal` | 0 | Body text |
| Wide | `--letter-spacing-wide` | 0.025em | Badges |
| Wider | `--letter-spacing-wider` | 0.05em | Labels, table headers (uppercase) |

## Heading Hierarchy

### H1 / Page Titles
```css
font-size: 1.75rem (28px)
font-weight: 700 (Bold)
line-height: 1.2
letter-spacing: -0.025em
color: #002A1B
```

**Usage**: Main page titles, dashboard welcome message

### H2 / Section Headers
```css
font-size: 1.5rem (24px)
font-weight: 700 (Bold)
line-height: 1.2
```

**Usage**: Major section dividers

### H3 / Card Titles
```css
font-size: 1.25rem (20px)
font-weight: 600 (Semibold)
line-height: 1.2
color: #002A1B
```

**Usage**: Card headers, subsection titles

### H4 / Subheadings
```css
font-size: 1.1rem (17.6px)
font-weight: 600 (Semibold)
line-height: 1.5
```

**Usage**: Form sections, content subheadings

### H5 / Small Headings
```css
font-size: 0.95rem (15.2px)
font-weight: 600 (Semibold)
line-height: 1.5
```

**Usage**: Alert headings, modal titles

### H6 / Micro Headings
```css
font-size: 0.9rem (14.4px)
font-weight: 600 (Semibold)
line-height: 1.5
```

**Usage**: Inline section labels

## Special Text Styles

### Dashboard Statistics
```css
font-size: 2.5rem (40px)
font-weight: 700 (Bold)
line-height: 1
color: #002A1B
```

### Form Labels
```css
font-size: 0.85rem (13.6px)
font-weight: 600 (Semibold)
text-transform: uppercase
letter-spacing: 0.05em
color: #495057
```

### Table Headers
```css
font-size: 0.85rem (13.6px)
font-weight: 600 (Semibold)
text-transform: uppercase
letter-spacing: 0.05em
color: #6c757d
```

### Body Text
```css
font-size: 0.9rem (14.4px)
font-weight: 400 (Normal)
line-height: 1.6
color: #212529
```

### Muted Text
```css
font-size: 0.85rem (13.6px)
color: #6c757d
```

### Badges
```css
font-size: 0.75rem (12px)
font-weight: 600 (Semibold)
text-transform: uppercase
letter-spacing: 0.025em
```

## Button System

### Button Sizes

#### Small Button (btn-sm)
```css
padding: 0.375rem 0.75rem
font-size: 0.85rem (13.6px)
min-height: 32px
border-radius: 0.375rem (6px)
```

**Usage**: Table actions, inline actions, compact spaces

#### Base Button (default)
```css
padding: 0.65rem 1.25rem
font-size: 0.9rem (14.4px)
min-height: 38px
border-radius: 0.5rem (8px)
```

**Usage**: Standard forms, primary actions, most common use

#### Large Button (btn-lg)
```css
padding: 0.75rem 1.5rem
font-size: 0.95rem (15.2px)
min-height: 44px
border-radius: 0.625rem (10px)
```

**Usage**: Hero sections, important CTAs, prominent actions

### Button Variants (All use Bufia Brand Green #047857)

#### Primary Button
```css
background-color: #047857
border-color: #047857
color: white
box-shadow: 0 2px 4px rgba(4, 120, 87, 0.2)

hover:
  background-color: #065F46
  transform: translateY(-1px)
  box-shadow: 0 4px 8px rgba(4, 120, 87, 0.3)
```

#### Success Button
```css
Same as Primary Button (uses Bufia brand green)
```

#### Outline Primary
```css
background-color: transparent
border-color: #047857
color: #047857

hover:
  background-color: #047857
  color: white
```

#### Secondary Button
```css
background-color: #6c757d
border-color: #6c757d
color: white
```

#### Danger Button
```css
background-color: #ef4444
border-color: #ef4444
color: white
```

#### Warning Button
```css
background-color: #f59e0b
border-color: #f59e0b
color: white
```

#### Info Button
```css
background-color: #3b82f6
border-color: #3b82f6
color: white
```

### Button Icons
- Icon size in small buttons: 0.75rem (12px)
- Icon size in base buttons: 0.875rem (14px)
- Icon size in large buttons: 1rem (16px)
- Icon spacing: 0.5rem from text

### Button States

#### Hover
- Darker background color
- Slight upward translation (-1px)
- Enhanced shadow

#### Active/Pressed
- Even darker background
- No translation
- Reduced shadow

#### Disabled
- 60% opacity
- No hover effects
- Cursor: not-allowed

#### Focus
- 2px outline in brand green
- 2px outline offset

## Usage Examples

### Page Header
```html
<div class="page-header">
    <h1 class="page-title">
        <i class="fas fa-tractor"></i>
        Equipment Management
    </h1>
</div>
```

### Card with Title
```html
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Recent Rentals</h3>
    </div>
    <div class="card-body">
        <p>Body text content goes here...</p>
    </div>
</div>
```

### Button Group
```html
<div class="d-flex gap-2">
    <button class="btn btn-primary">
        <i class="fas fa-save"></i>
        Save Changes
    </button>
    <button class="btn btn-outline-secondary">
        Cancel
    </button>
</div>
```

### Form with Labels
```html
<div class="mb-3">
    <label for="machineName" class="form-label">Machine Name</label>
    <input type="text" class="form-control" id="machineName">
</div>
```

### Table with Actions
```html
<table class="table">
    <thead>
        <tr>
            <th>Machine</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Tractor Model X</td>
            <td><span class="badge bg-success">Available</span></td>
            <td>
                <div class="action-btn-group">
                    <button class="btn btn-sm btn-primary">View</button>
                    <button class="btn btn-sm btn-outline-secondary">Edit</button>
                </div>
            </td>
        </tr>
    </tbody>
</table>
```

## Responsive Behavior

### Desktop (> 992px)
- All font sizes at full scale
- Full button padding

### Tablet (768px - 992px)
- Page titles: 1.5rem
- Stats: 2rem
- Standard button sizes

### Mobile (< 768px)
- Page titles: 1.375rem
- Section headers: 1.25rem
- Stats: 1.75rem
- Buttons: Slightly reduced padding
- Small buttons: 0.375rem 0.75rem

## Accessibility

### Focus States
- All interactive elements have visible focus indicators
- 2px solid outline in brand green (#047857)
- 2px outline offset for clarity

### Color Contrast
- All text meets WCAG AA standards
- Minimum contrast ratio of 4.5:1 for body text
- Minimum contrast ratio of 3:1 for large text

### Font Smoothing
- `-webkit-font-smoothing: antialiased`
- `-moz-osx-font-smoothing: grayscale`

## Implementation

The typography and button system is implemented in:
- `static/css/typography-system.css` - Main system file
- Loaded in `templates/base.html` after Bootstrap
- Overrides Bootstrap defaults with Bufia brand styles

## Benefits

1. **Consistency**: All pages use the same text sizes and button dimensions
2. **Readability**: Optimized font sizes and line heights for easy reading
3. **Brand Identity**: Consistent use of Bufia brand green across all buttons
4. **Accessibility**: Proper heading hierarchy and focus states
5. **Maintainability**: Centralized system using CSS variables
6. **Responsive**: Scales appropriately on all device sizes
7. **Professional**: Clean, modern appearance matching the dashboard design
