# ✅ Machine Type Field Fix - Edit Page

## 🎯 **Issue Identified**

When editing a machine at `http://127.0.0.1:8000/machines/21/edit/`, the machine_type field was not appearing in the form.

## 🔍 **Root Cause**

In `machines/views.py`, the `MachineUpdateView` class had two issues:

1. **Line 2195**: `show_machine_type_field` was hardcoded to `False`
2. **Line 2215**: `hide_machine_type` was hardcoded to `True`

This caused the machine_type field to always be hidden as a hidden input field, even for regular machines where it should be visible.

## ✅ **Fix Applied**

### **File: machines/views.py**

**Changed in `MachineUpdateView.get_context_data()`:**
```python
# BEFORE:
context['show_machine_type_field'] = False

# AFTER:
context['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request, self.object)
context['show_machine_type_field'] = not context['is_dryer_setup_flow']
```

**Changed in `MachineUpdateView.get_form_kwargs()`:**
```python
# BEFORE:
kwargs['hide_machine_type'] = True

# AFTER:
kwargs['is_dryer_setup_flow'] = _is_dryer_setup_flow(self.request, self.object)
kwargs['hide_machine_type'] = kwargs['is_dryer_setup_flow']
```

## 🎯 **Logic**

The fix implements the correct logic:

- **For Regular Machines** (tractors, harvesters, etc.):
  - `show_machine_type_field = True` → Field is visible as a select dropdown
  - `hide_machine_type = False` → Field is not hidden
  
- **For Dryer Setup Flow**:
  - `show_machine_type_field = False` → Field is hidden
  - `hide_machine_type = True` → Field rendered as hidden input

## 📋 **How It Works**

### **Template Logic (templates/machines/machine_form.html)**

```html
<!-- If show_machine_type_field is False, render as hidden -->
{% if not show_machine_type_field %}
{{ form.machine_type }}
{% endif %}

<!-- If show_machine_type_field is True, render as visible select -->
{% if show_machine_type_field %}
<div class="field-card form-group" id="div_id_machine_type">
    <label class="form-label">Machine type</label>
    {{ form.machine_type }}
</div>
{% endif %}
```

### **Form Logic (machines/forms.py)**

```python
if self.hide_machine_type:
    self.fields['machine_type'].widget = forms.HiddenInput()
```

## 🔄 **To Apply the Fix**

1. **Restart Django Server**: The code changes are in place, but Django needs to reload
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart:
   python manage.py runserver
   ```

2. **Clear Browser Cache**: If needed, do a hard refresh (Ctrl+F5)

3. **Verify**: Navigate to `http://127.0.0.1:8000/machines/21/edit/`
   - The "Machine type" field should now be visible as a dropdown
   - It should show the current machine type selected

## ✅ **Expected Result**

After restarting the Django server:

- **Regular machines** (tractors, harvesters, etc.): Machine type field is VISIBLE
- **Dryer machines** (in dryer setup flow): Machine type field is HIDDEN
- **Rice mill machines**: Machine type field behavior depends on context

## 📍 **Files Modified**

- `machines/views.py` - Lines 2195-2218 (MachineUpdateView class)

## 🎉 **Summary**

The machine_type field will now correctly appear when editing regular machines, while remaining hidden for dryer setup flows where the type is pre-selected and shouldn't be changed.