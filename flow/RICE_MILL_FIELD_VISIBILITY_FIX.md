# Rice Mill Field Visibility Fix

## Issue
The rice mill dropdown was still showing (with dashes "--------") instead of being hidden and replaced with an info alert. Users couldn't input other fields because the dropdown was blocking them.

## Root Cause
The template was checking `form.machine.field.widget.input_type == 'hidden'` which wasn't reliably detecting the HiddenInput widget in Django templates.

## Solution
Changed the template to use the `single_rice_mill` context variable that the view explicitly sets when there's only one rice mill available.

## Changes Made

### Template Fix (`machines/templates/machines/ricemill_appointment_form.html`)

**Before:**
```django
{% if form.machine.field.widget.input_type == 'hidden' %}
    <!-- Show info alert -->
{% else %}
    <!-- Show dropdown -->
{% endif %}
```

**After:**
```django
{% if single_rice_mill %}
    <!-- Show info alert -->
    {{ form.machine }}  <!-- Hidden input -->
    <div class="alert alert-info mb-3">
        <i class="fas fa-info-circle me-2"></i>
        <strong>Rice Mill:</strong> {{ machine.name }}
        <small class="d-block mt-1">This is the only rice mill available.</small>
    </div>
{% else %}
    <!-- Show dropdown -->
{% endif %}
```

## How It Works

1. **View detects single rice mill:**
   ```python
   rice_mills = Machine.objects.filter(machine_type='rice_mill')
   if rice_mills.count() == 1:
       context['machine'] = rice_mills.first()
       context['single_rice_mill'] = True  # Flag for template
   ```

2. **Form hides the field:**
   ```python
   if rice_mills.count() == 1:
       self.fields['machine'].widget = forms.HiddenInput()
   ```

3. **Template uses context flag:**
   ```django
   {% if single_rice_mill %}
       <!-- Hidden field + info alert -->
   {% else %}
       <!-- Normal dropdown -->
   {% endif %}
   ```

## Benefits

✅ **Reliable Detection** - Uses explicit context variable instead of widget introspection
✅ **Clean UI** - No dropdown shown when only one option exists
✅ **Direct Input** - Users can immediately input appointment date
✅ **Clear Communication** - Info alert shows which rice mill is selected
✅ **Maintains Data** - Hidden input still submits the machine value

## Result

### Before (Broken)
```
Rice Mill
[--------- ▼]  <-- Dropdown showing dashes
[--------- ]
[--------- ]

dd/mm/yyyy  <-- Can't click here
```

### After (Fixed)
```
ℹ️ Rice Mill: BUFIA Rice Mill
This is the only rice mill available.

Appointment Date
[dd/mm/yyyy]  <-- Can click directly here ✓
```

## Testing

1. Navigate to `/machines/rice-mill-appointments/create/`
2. Verify NO dropdown is shown
3. Verify info alert is displayed with rice mill name
4. Verify appointment date field is immediately accessible
5. Verify you can click and type in the date field
6. Verify form submits successfully

## Files Modified

1. **machines/templates/machines/ricemill_appointment_form.html**
   - Changed from widget type check to context variable check
   - Now uses `{% if single_rice_mill %}` instead of widget introspection

## Related Files

- **machines/views.py** - Sets `single_rice_mill` context variable
- **machines/forms.py** - Converts field to HiddenInput widget

## Why This Fix Works

Django templates have limited introspection capabilities for widget types. Checking `widget.input_type` doesn't always work reliably, especially with custom widgets or after form initialization.

Using an explicit context variable (`single_rice_mill`) is:
- More reliable
- Easier to understand
- Explicitly controlled by the view
- Not dependent on Django's internal widget implementation

## Result

🎉 **Perfect form with:**
- No dropdown when only one rice mill exists
- Clear info message showing the selected rice mill
- Direct access to appointment date field
- Users can immediately start inputting their appointment details
- Form submits correctly with the hidden machine value
