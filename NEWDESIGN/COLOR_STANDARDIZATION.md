# Bufia Brand Color Standardization

## Overview
All green colors across the application have been standardized to use the official Bufia brand green color palette.

## Bufia Brand Green Color Palette

### Primary Colors
- **Primary Green**: `#047857` (Main brand color)
- **Primary Dark**: `#065F46` (Hover states, darker accents)
- **Primary Darker**: `#064E3B` (Deep accents)
- **Primary Light**: `#10b981` (Light accents, gradients)
- **Primary Lighter**: `#D1FAE5` (Backgrounds, badges)

## Changes Made

### 1. base.html
✅ Already using correct Bufia brand green (`#047857`)
- CSS variables properly defined
- All buttons and UI elements use the brand color

### 2. static/css/bufia-design-system.css
Updated from inconsistent greens to Bufia brand green:
- Changed `--primary` from `#1DBC60` to `#047857`
- Changed `--primary-dark` from `#17A34A` to `#065F46`
- Changed `--primary-light` from `#4ADE80` to `#10b981`
- Changed `--success` from `#1DBC60` to `#047857`
- Updated all gradient backgrounds
- Updated all box shadows with correct rgba values
- Updated all badges to use brand green

### 3. static/css/unified-design-system.css
Updated from inconsistent greens to Bufia brand green:
- Changed `--primary` from `#1DBC60` to `#047857`
- Changed `--primary-dark` from `#17A34A` to `#065F46`
- Changed `--primary-darker` from `#0D4D18` to `#064E3B`
- Changed `--primary-light` from `#4CAF50` to `#10b981`
- Changed `--primary-lighter` from `#C8E6C9` to `#D1FAE5`
- Changed `--success` from `#1DBC60` to `#047857`
- Updated all button styles
- Updated all page headers
- Updated all form focus states
- Updated all badges
- Updated all alerts
- Updated all action buttons
- Updated all avatar placeholders
- Updated all user thumbnails

### 4. static/css/button-styles.css
Updated from inconsistent greens to Bufia brand green:
- Changed primary button gradients from `#2E7D32/#4CAF50` to `#047857/#10b981`
- Changed success button gradients from `#28a745/#20c997` to `#047857/#10b981`
- Changed outline button borders to use `#047857`
- Changed link button colors to use `#047857/#065F46`
- Updated focus-visible outline to use brand green rgba

## Color Usage Guidelines

### When to Use Each Shade

1. **Primary Green (#047857)**
   - Main buttons (primary, success)
   - Brand logo text
   - Active navigation items
   - Primary CTAs
   - Links

2. **Primary Dark (#065F46)**
   - Button hover states
   - Active/pressed states
   - Darker text on light backgrounds
   - Secondary accents

3. **Primary Darker (#064E3B)**
   - Deep shadows
   - Very dark accents
   - High contrast elements

4. **Primary Light (#10b981)**
   - Gradient endpoints
   - Light hover states
   - Subtle highlights

5. **Primary Lighter (#D1FAE5)**
   - Background tints
   - Badge backgrounds
   - Hover backgrounds for nav items
   - Success alert backgrounds

## Benefits of Standardization

1. **Brand Consistency**: All green elements now match the official Bufia brand color
2. **Visual Harmony**: Consistent color palette creates a more professional appearance
3. **Easier Maintenance**: Single source of truth for brand colors
4. **Better UX**: Users can easily identify interactive elements and brand elements
5. **Accessibility**: Consistent color usage improves recognition and usability

## Testing Checklist

- [ ] All buttons display the correct Bufia green
- [ ] Navigation items use the brand green when active
- [ ] Page headers use the brand green gradient
- [ ] Form focus states show the brand green
- [ ] Badges and status indicators use the brand green
- [ ] Hover states transition to the darker brand green
- [ ] Success messages and alerts use the brand green
- [ ] All gradients flow smoothly with the brand colors

## Notes

- No inline styles were found that needed updating
- All CSS files now reference the same color values
- The color palette is defined in CSS variables for easy future updates
- All rgba values have been updated to match the new hex colors
