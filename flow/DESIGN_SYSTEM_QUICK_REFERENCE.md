# BUFIA Design System - Quick Reference Card

## 🎨 Color Palette

```css
/* Primary */
--primary: #2E7D32        /* Agriculture Green */
--accent: #0288D1         /* Irrigation Blue */

/* Semantic */
--success: #198754        /* Green */
--warning: #FFC107        /* Yellow */
--danger: #DC3545         /* Red */
--info: #0DCAF0          /* Cyan */

/* Neutrals */
--gray-50: #F8F9FA       /* Background */
--gray-600: #6C757D      /* Muted text */
--gray-900: #212529      /* Primary text */
```

## 📦 Stat Card (Icon-Based)

```html
<div class="col-md-4 mb-3">
    <div class="card border-0 shadow-sm h-100">
        <div class="card-body">
            <div class="d-flex align-items-center">
                <div class="flex-shrink-0 bg-warning bg-opacity-25 p-3 rounded">
                    <i class="fas fa-clock text-warning fa-2x"></i>
                </div>
                <div class="flex-grow-1 ms-3">
                    <h6 class="text-muted mb-1">Label</h6>
                    <h3 class="mb-0">Value</h3>
                </div>
            </div>
        </div>
    </div>
</div>
```

**Color Variants:**
- `bg-warning` + `text-warning` (Yellow)
- `bg-success` + `text-success` (Green)
- `bg-info` + `text-info` (Cyan)
- `bg-primary` + `text-primary` (Blue)
- `bg-danger` + `text-danger` (Red)

## 📋 Data Table

```html
<div class="card shadow-sm border-0">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Column 1</th>
                        <th>Column 2</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Data 1</td>
                        <td>Data 2</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
```

## 🔍 Filter Card

```html
<div class="card shadow-sm border-0 mb-4">
    <div class="card-header bg-light">
        <h5 class="mb-0">
            <i class="fas fa-filter me-2"></i> Filters
        </h5>
    </div>
    <div class="card-body">
        <form method="get" class="row g-3">
            <div class="col-md-3">
                <label for="field" class="form-label">Label</label>
                <select name="field" id="field" class="form-select">
                    <option value="">All</option>
                </select>
            </div>
            <div class="col-md-3 d-flex align-items-end">
                <button type="submit" class="btn btn-primary me-2">
                    <i class="fas fa-search me-1"></i> Apply
                </button>
                <a href="#" class="btn btn-outline-secondary">
                    <i class="fas fa-redo me-1"></i> Reset
                </a>
            </div>
        </form>
    </div>
</div>
```

## 🏷️ Badges

```html
<span class="badge bg-warning text-dark">Pending</span>
<span class="badge bg-success">Approved</span>
<span class="badge bg-danger">Rejected</span>
<span class="badge bg-info">Completed</span>
<span class="badge bg-secondary">Cancelled</span>
```

## 🔘 Buttons

```html
<!-- Primary -->
<button class="btn btn-primary">
    <i class="fas fa-search me-1"></i> Primary
</button>

<!-- Secondary -->
<button class="btn btn-outline-secondary">
    <i class="fas fa-redo me-1"></i> Secondary
</button>

<!-- Small -->
<a href="#" class="btn btn-sm btn-primary">
    <i class="fas fa-edit me-1"></i> Small
</a>
```

## 📄 Page Header

```html
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h3 class="mb-0">Page Title</h3>
        <p class="text-muted">Description</p>
    </div>
    <div>
        <a href="#" class="btn btn-outline-primary">
            <i class="fas fa-plus me-1"></i> Action
        </a>
    </div>
</div>
```

## 📭 Empty State

```html
<div class="text-center py-5">
    <div class="mb-3">
        <i class="fas fa-inbox fa-4x text-muted"></i>
    </div>
    <h5>No Items Found</h5>
    <p class="text-muted">Description text here</p>
</div>
```

## 📐 Layout Structure

```html
<div class="container-fluid py-4">
    <!-- 1. Page Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <!-- Header content -->
    </div>
    
    <!-- 2. Stat Cards -->
    <div class="row mb-4">
        <!-- 3-4 stat cards -->
    </div>
    
    <!-- 3. Filters (Optional) -->
    <div class="card shadow-sm border-0 mb-4">
        <!-- Filter form -->
    </div>
    
    <!-- 4. Main Content -->
    <div class="card shadow-sm border-0">
        <!-- Table or content -->
    </div>
</div>
```

## 📱 Responsive Grid

```html
<!-- 3 columns on desktop, stack on mobile -->
<div class="row mb-4">
    <div class="col-md-4 mb-3"><!-- Card 1 --></div>
    <div class="col-md-4 mb-3"><!-- Card 2 --></div>
    <div class="col-md-4 mb-3"><!-- Card 3 --></div>
</div>

<!-- 4 columns for filters -->
<div class="row g-3">
    <div class="col-md-3"><!-- Filter 1 --></div>
    <div class="col-md-3"><!-- Filter 2 --></div>
    <div class="col-md-3"><!-- Filter 3 --></div>
    <div class="col-md-3"><!-- Buttons --></div>
</div>
```

## 🎯 Common Classes

```css
/* Spacing */
.mb-0, .mb-1, .mb-2, .mb-3, .mb-4, .mb-5
.me-1, .me-2, .me-3
.ms-3
.py-4, .py-5
.p-0

/* Display */
.d-flex
.align-items-center
.align-items-end
.justify-content-between

/* Sizing */
.h-100

/* Text */
.text-muted
.text-center

/* Shadows */
.shadow-sm
```

## ✅ Checklist

When creating a new page:
- [ ] Use `container-fluid py-4` wrapper
- [ ] Add page header with title and description
- [ ] Use icon-based stat cards (3-4 cards)
- [ ] Add filter card if needed
- [ ] Use `card shadow-sm border-0` for containers
- [ ] Tables: `table table-hover mb-0` with `table-light` header
- [ ] Badges for status indicators
- [ ] Buttons with icons and `me-1` spacing
- [ ] Empty state for no data
- [ ] Test responsive behavior

## 📚 Resources

- Full Guide: `BUFIA_DESIGN_SYSTEM_GUIDE.md`
- CSS File: `static/css/bufia-design-system.css`
- Reference: `/irrigation/admin/requests/`
- Icons: Font Awesome 6.x
