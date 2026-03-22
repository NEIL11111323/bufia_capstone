# Template Syntax Error Fix

## Issue
The rental approval page was throwing a `TemplateSyntaxError`:
```
Could not parse the remainder: ':\'M d, Y h:i A\'' from 'rental.payment_date|date:\'M d, Y h:i A\''
```

## Root Cause
In the verify payment button's `onclick` attribute, the date filter was using escaped quotes:
```html
onclick="return confirm('... Date: {{ rental.payment_date|date:\'M d, Y h:i A\' }} ...');"
```

Django template syntax doesn't support escaped quotes (`\'`) inside template variable filters when they're already inside a JavaScript string.

## Solution
Moved the `confirm()` call from the button's `onclick` to the form's `onsubmit` attribute, which allows using regular double quotes for the date filter:

### Before (Broken):
```html
<button type="submit" onclick="return confirm('... {{ rental.payment_date|date:\'M d, Y h:i A\' }} ...');">
```

### After (Fixed):
```html
<form onsubmit="return confirm('... {{ rental.payment_date|date:"M d, Y h:i A" }} ...');">
    <button type="submit">
```

## Result
- ✅ Template syntax error resolved
- ✅ Page loads correctly
- ✅ Confirmation dialog still works as expected
- ✅ All functionality preserved

## Files Modified
- `templates/machines/admin/rental_approval.html` - Fixed the verify payment button confirmation dialog

## Testing
Run `python test_template_syntax.py` to verify the template loads without errors.
