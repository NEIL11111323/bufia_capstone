# Design Document: Sidebar Scroll Preservation

## Overview

This design addresses the sidebar scroll position preservation issue where clicking any navigation link causes the sidebar to jump to the top. The solution involves implementing a robust scroll position tracking and restoration mechanism using browser storage APIs and proper event handling to ensure users maintain their scroll context when navigating between pages.

## Architecture

The solution follows a client-side JavaScript approach with three main components:

1. **Scroll Position Tracker**: Monitors and saves sidebar scroll position
2. **Position Restorer**: Restores saved scroll position on page load
3. **Event Handler Manager**: Coordinates scroll events and navigation actions

The architecture uses `sessionStorage` instead of `localStorage` to ensure scroll positions are session-specific and don't persist across browser sessions, providing a more natural user experience.

## Components and Interfaces

### 1. Scroll Position Tracker

**Purpose**: Continuously monitor and save the sidebar's scroll position

**Key Functions**:
- `saveSidebarScrollPosition()`: Saves current scroll position to sessionStorage
- `debouncedSaveScroll()`: Debounced version to prevent excessive storage writes

**Storage Key**: `sidebarScrollPosition`

**Data Format**: Integer representing `scrollTop` value in pixels

### 2. Position Restorer

**Purpose**: Restore the saved scroll position when the page loads

**Key Functions**:
- `restoreSidebarScrollPosition()`: Retrieves and applies saved scroll position
- `smoothScrollToPosition(position)`: Applies scroll position with optional smooth behavior

**Timing**: Executes on `DOMContentLoaded` and after sidebar is fully rendered

### 3. Event Handler Manager

**Purpose**: Coordinate all scroll-related events and navigation actions

**Key Events**:
- `scroll`: Track scroll position changes
- `click`: Save position before navigation
- `beforeunload`: Final save before page unload
- `DOMContentLoaded`: Restore position on page load

## Data Models

### Scroll Position Data

```javascript
{
  key: "sidebarScrollPosition",
  value: number, // scrollTop in pixels
  storage: sessionStorage
}
```

### Sidebar State

```javascript
{
  element: HTMLElement, // sidebar DOM element
  scrollTop: number,    // current scroll position
  scrollHeight: number, // total scrollable height
  clientHeight: number  // visible height
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Scroll position persistence across navigation

*For any* sidebar scroll position when a user clicks a navigation link, the scroll position saved to sessionStorage should equal the scroll position before the click occurred.

**Validates: Requirements 1.1, 1.4**

### Property 2: Scroll position restoration accuracy

*For any* saved scroll position value in sessionStorage, when the page loads and the sidebar is rendered, the sidebar's scrollTop should equal the saved value.

**Validates: Requirements 1.2, 1.4**

### Property 3: Scroll position independence from link location

*For any* navigation link in the sidebar (top, middle, or bottom), clicking it should preserve the current scroll position regardless of the link's position in the DOM.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 4: Dropdown interaction scroll stability

*For any* dropdown menu interaction (open/close), the sidebar scroll position should remain unchanged before and after the interaction.

**Validates: Requirements 2.1, 2.2**

### Property 5: Storage operation idempotence

*For any* scroll position value, saving it multiple times in quick succession should result in the same stored value as saving it once.

**Validates: Requirements 3.1, 3.3**

## Error Handling

### Storage Availability

**Issue**: sessionStorage may not be available (private browsing, storage quota exceeded)

**Solution**: 
```javascript
function isStorageAvailable() {
  try {
    const test = '__storage_test__';
    sessionStorage.setItem(test, test);
    sessionStorage.removeItem(test);
    return true;
  } catch(e) {
    return false;
  }
}
```

**Fallback**: If storage is unavailable, the system continues to function but without scroll preservation.

### Sidebar Element Not Found

**Issue**: Sidebar element may not exist on certain pages

**Solution**: Check for element existence before attempting to access scroll properties

```javascript
const sidebar = document.getElementById('sidebar');
if (!sidebar) return;
```

### Invalid Scroll Position

**Issue**: Stored scroll position may be invalid (negative, NaN, exceeds scrollHeight)

**Solution**: Validate and clamp scroll position before applying

```javascript
function validateScrollPosition(position, maxScroll) {
  const parsed = parseInt(position);
  if (isNaN(parsed) || parsed < 0) return 0;
  if (parsed > maxScroll) return maxScroll;
  return parsed;
}
```

### Race Conditions

**Issue**: Multiple navigation clicks in quick succession

**Solution**: Use debouncing for scroll saves and ensure last save wins

```javascript
let saveTimeout;
function debouncedSave(position) {
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    sessionStorage.setItem('sidebarScrollPosition', position);
  }, 100);
}
```

## Testing Strategy

### Unit Tests

Unit tests will verify specific behaviors and edge cases:

1. **Storage Operations**
   - Test saving scroll position to sessionStorage
   - Test retrieving scroll position from sessionStorage
   - Test handling of missing/invalid stored values

2. **Position Validation**
   - Test clamping of negative scroll values
   - Test clamping of values exceeding scrollHeight
   - Test handling of NaN values

3. **Element Existence**
   - Test behavior when sidebar element doesn't exist
   - Test behavior when sessionStorage is unavailable

### Property-Based Tests

Property-based tests will verify universal behaviors across many inputs:

1. **Scroll Position Round-Trip** (Property 1 & 2)
   - Generate random valid scroll positions (0 to scrollHeight)
   - Save position, simulate page reload, restore position
   - Verify restored position equals original position

2. **Link Position Independence** (Property 3)
   - Generate random sidebar scroll positions
   - Generate random link positions in sidebar
   - Click link, verify scroll position unchanged before navigation

3. **Dropdown Stability** (Property 4)
   - Generate random scroll positions
   - Open/close dropdowns at various positions
   - Verify scroll position unchanged

4. **Storage Idempotence** (Property 5)
   - Generate random scroll position
   - Save it N times (where N is random 1-100)
   - Verify stored value equals original value

### Integration Tests

1. **Full Navigation Flow**
   - User scrolls to bottom of sidebar
   - User clicks "Activity Logs"
   - Verify sidebar remains at bottom on new page

2. **Cross-Page Persistence**
   - Navigate through multiple pages
   - Verify scroll position maintained across all navigations

3. **Mobile Responsive Behavior**
   - Test scroll preservation on mobile collapsed sidebar
   - Verify no interference with mobile overlay behavior

### Manual Testing Checklist

1. Scroll to bottom, click any link → sidebar stays at bottom
2. Scroll to middle, click any link → sidebar stays at middle
3. Open dropdown, click link inside → scroll position maintained
4. Rapid clicks on multiple links → no scroll jumping
5. Browser back/forward → scroll position restored correctly
6. Page refresh → scroll position restored correctly
7. Mobile view → scroll behavior works correctly

## Implementation Notes

### Current Problem Analysis

The existing code has a flawed approach:

```javascript
// PROBLEM: This saves position but page navigates away immediately
sidebar.addEventListener('click', function(e) {
    if (e.target.tagName === 'A' || e.target.closest('a')) {
        localStorage.setItem('sidebarScrollPos', sidebar.scrollTop);
    }
});
```

The issue is that the scroll position is saved, but then the restoration logic may not execute properly or may be overridden by other scroll events.

### Proposed Solution

1. **Remove conflicting scroll logic**: Remove the existing `beforeunload` and click-based save logic
2. **Implement continuous tracking**: Save scroll position on scroll events (debounced)
3. **Restore on load**: Apply saved position immediately after DOM is ready
4. **Use sessionStorage**: More appropriate for session-specific UI state

### Key Implementation Details

- **Debounce delay**: 150ms for scroll saves (balance between responsiveness and performance)
- **Restoration timing**: Use `requestAnimationFrame` to ensure DOM is fully rendered
- **Storage key**: Use descriptive key like `bufia_sidebar_scroll_position`
- **Cleanup**: Clear stored position on logout or session end

## Performance Considerations

1. **Debouncing**: Prevent excessive storage writes during scroll
2. **Event delegation**: Use single event listener instead of multiple
3. **Early returns**: Check element existence before operations
4. **Minimal DOM queries**: Cache sidebar element reference

## Browser Compatibility

- sessionStorage: Supported in all modern browsers (IE8+)
- scrollTop property: Universal support
- requestAnimationFrame: Supported in all modern browsers (IE10+)

Fallback for older browsers: Feature detection with graceful degradation.
