# Machine Card Visual Guide

## Enhanced Machine Card Layout

### Complete Card Structure

```
┌─────────────────────────────────────────────────┐
│ [Available]                    [Rice Mill]      │ ← Status & Type Badges
│                                                  │
│              Machine Image                       │ ← 200px height
│         (or placeholder icon)                    │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  BUFIA Rice Mill                                 │ ← Machine Name (bold)
│                                                  │
│  Community rice mill for processing paddy rice   │ ← Description (3 lines max)
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ 🔧 Type: Rice Mill                      │   │ ← Specs Box
│  │ ⏰ Rate: ₱150/hour                      │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ─────────────────────────────────────────────  │
│              ₱150 /hour                          │ ← Main Pricing
│  ─────────────────────────────────────────────  │
│                                                  │
│  [👁 View]  [🤝 Rent]  [✏ Edit]  [🗑 Delete]   │ ← Action Buttons
│                                                  │
└─────────────────────────────────────────────────┘
```

## Different Machine Types Display

### 1. Rice Mill
```
┌─────────────────────────────────┐
│ [Available]      [Rice Mill]    │
│        🌾 Image                  │
├─────────────────────────────────┤
│ BUFIA Rice Mill                 │
│ Community rice mill...          │
│                                 │
│ ┌─────────────────────────────┐│
│ │ 🔧 Type: Rice Mill          ││
│ │ ⏰ Rate: ₱150/hour          ││
│ └─────────────────────────────┘│
│                                 │
│ ──────────────────────────────  │
│        ₱150 /hour               │
│ ──────────────────────────────  │
│                                 │
│ [View] [Rent]                   │
└─────────────────────────────────┘
```

### 2. 4-Wheel Drive Tractor
```
┌─────────────────────────────────┐
│ [Available]      [Tractor]      │
│        🚜 Image                  │
├─────────────────────────────────┤
│ 4-Wheel Drive Tractor           │
│ Heavy-duty tractor for...       │
│                                 │
│ ┌─────────────────────────────┐│
│ │ 🔧 Type: 4WD Tractor        ││
│ │ 📅 Rental: ₱4000/day        ││
│ └─────────────────────────────┘│
│                                 │
│ ──────────────────────────────  │
│       ₱4000 /hectare            │
│ ──────────────────────────────  │
│                                 │
│ [View] [Rent]                   │
└─────────────────────────────────┘
```

### 3. Hand Tractor
```
┌─────────────────────────────────┐
│ [Available]   [Hand Tractor]    │
│        🚜 Image                  │
├─────────────────────────────────┤
│ Hand Tractor                    │
│ Compact tractor for small...    │
│                                 │
│ ┌─────────────────────────────┐│
│ │ 🔧 Type: Hand Tractor       ││
│ │ 📅 Rental: ₱1000/day        ││
│ └─────────────────────────────┘│
│                                 │
│ ──────────────────────────────  │
│       ₱1000 flat rate           │
│ ──────────────────────────────  │
│                                 │
│ [View] [Rent]                   │
└─────────────────────────────────┘
```

### 4. Harvester
```
┌─────────────────────────────────┐
│ [Available]     [Harvester]     │
│        🌾 Image                  │
├─────────────────────────────────┤
│ Rice Harvester                  │
│ Efficient harvesting machine... │
│                                 │
│ ┌─────────────────────────────┐│
│ │ 🔧 Type: Harvester          ││
│ │ 📅 Rental: (varies)/day     ││
│ └─────────────────────────────┘│
│                                 │
│ ──────────────────────────────  │
│         1/9 /sack               │
│ ──────────────────────────────  │
│                                 │
│ [View] [Rent]                   │
└─────────────────────────────────┘
```

## Color Scheme

### Status Badges
- **Available**: Green background (#2ecc71)
- **Unavailable**: Red background (#e74c3c)
- **Maintenance**: Orange background (#f39c12)

### Type Badges
- **Background**: Dark semi-transparent (#000 70% opacity)
- **Text**: White
- **Hover**: BUFIA Green (#00a86b)

### Specs Box
- **Background**: Light gray (#f8faf9)
- **Border**: Light border (#e2e8f0)
- **Icons**: Colored (primary, success, info)

### Pricing
- **Color**: BUFIA Green (#00a86b)
- **Font**: Bold, 1.3rem
- **Border**: Top border separator

### Buttons
- **View**: BUFIA Green (#00a86b)
- **Rent**: Success Green (#2ecc71)
- **Edit**: Light gray with border
- **Delete**: White with red text

## Icon Reference

### Specs Icons
- 🔧 `fas fa-cog` - Machine type (primary color)
- ⏰ `fas fa-clock` - Hourly rate (success color)
- 📅 `fas fa-calendar-day` - Daily rental (info color)

### Button Icons
- 👁 `fa-regular fa-eye` - View details
- 🤝 `fa-solid fa-handshake` - Rent machine
- ✏ `fa-regular fa-pen-to-square` - Edit
- 🗑 `fa-regular fa-trash-can` - Delete

## Responsive Breakpoints

### Mobile (< 576px)
```
┌─────────────────┐
│ [Status] [Type] │
│     Image       │
├─────────────────┤
│ Name            │
│ Description     │
│                 │
│ ┌─────────────┐│
│ │ Specs       ││
│ └─────────────┘│
│                 │
│ ──────────────  │
│    Pricing      │
│ ──────────────  │
│                 │
│ [View]          │
│ [Rent]          │
│ [Edit]          │
│ [Delete]        │
└─────────────────┘
```
- 1 column layout
- Full-width buttons
- Stacked vertically

### Tablet (576px - 991px)
```
┌──────────┐ ┌──────────┐
│ Machine  │ │ Machine  │
│ Card 1   │ │ Card 2   │
└──────────┘ └──────────┘
```
- 2 columns
- Compact layout
- Touch-friendly

### Desktop (> 992px)
```
┌────┐ ┌────┐ ┌────┐ ┌────┐
│ M1 │ │ M2 │ │ M3 │ │ M4 │
└────┘ └────┘ └────┘ └────┘
```
- 3-4 columns
- Full specs visible
- Hover effects

## Hover Effects

### Card Hover
```
Before:
┌─────────────┐
│   Machine   │
└─────────────┘

After Hover:
┌─────────────┐
│   Machine   │ ← Lifts up 8px
└─────────────┘
  ↑ Shadow increases
  ↑ Border turns green
```

### Button Hover
```
Before:
[View]

After Hover:
[View] ← Lifts up 2px
  ↑ Shadow increases
  ↑ Background darkens
```

### Image Hover
```
Before:
[Image at 100%]

After Hover:
[Image at 105%] ← Zooms in slightly
```

## Spacing & Sizing

### Card Dimensions
- **Min Height**: 320px
- **Border Radius**: 16px
- **Border**: 2px solid
- **Padding**: 1.25rem

### Image Container
- **Height**: 200px
- **Border Radius**: 14px (top only)
- **Overflow**: Hidden

### Specs Box
- **Padding**: 0.75rem
- **Border Radius**: 8px
- **Margin**: 0.75rem 0

### Buttons
- **Min Height**: 38px
- **Border Radius**: 8px
- **Font Size**: 0.8rem
- **Gap**: 6px between buttons

## Animation Timing

### Card Entrance
- **Delay**: Staggered (0.1s per card)
- **Duration**: 0.5s
- **Effect**: Fade in + slide up

### Hover Transitions
- **Duration**: 0.3s
- **Easing**: ease
- **Properties**: transform, box-shadow, border-color

### Button Interactions
- **Duration**: 0.2s
- **Easing**: ease
- **Properties**: transform, background-color

## Accessibility

### ARIA Labels
- View button: "View machine details"
- Rent button: "Rent this machine"
- Edit button: "Edit machine details"
- Delete button: "Delete machine"

### Keyboard Navigation
- All buttons are focusable
- Focus outline: 2px solid primary color
- Tab order: View → Rent → Edit → Delete

### Screen Readers
- Status badges announce availability
- Type badges announce machine type
- Pricing clearly labeled with units

## Summary

✅ **Clear Information Hierarchy**: Most important info first
✅ **Visual Consistency**: Same layout for all machines
✅ **Responsive Design**: Works on all screen sizes
✅ **Accessible**: Keyboard and screen reader friendly
✅ **Professional**: Clean, modern design
✅ **User-Friendly**: Easy to scan and compare

The enhanced machine cards provide all necessary information at a glance while maintaining a clean, professional appearance.
