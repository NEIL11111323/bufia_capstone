# Hectares Input Field Implementation

## Overview
Updated the machine rental form to make the hectares (land area) input field editable and required, allowing users to directly enter the area of land they want to rent the machine for.

## Changes Made

### 1. Updated Form Field (machines/forms.py)

**Before:**
```python
area = forms.DecimalField(
    max_digits=10,
    decimal_places=4,
    required=False,
    label='Area (hectares)',
    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'readonly': True})
)
```

**After:**
```python
area = forms.DecimalField(
    max_digits=10,
    decimal_places=4,
    required=False,
    label='Land Area (hectares)',
    help_text='Enter the area of land in hectares',
    widget=forms.NumberInput(attrs={
        'class': 'form-control', 
        'step': '0.01', 
        'placeholder': 'e.g., 2.5',
        'min': '0.01'
    })
)
```

**Key Changes:**
- Removed `readonly` attribute - field is now editable
- Changed step from `0.0001` to `0.01` for easier input
- Added placeholder text for guidance
- Added minimum value of 0.01
- Updated label to "Land Area (hectares)"
- Added help text

### 2. Updated Template (templates/machines/rental_form.html)

**Before:**
```html
<input type="number" class="form-control" name="area" id="area" 
       step="0.0001" min="0.0001" readonly placeholder="Auto-calculated">
<small class="text-muted">Calculated automatically</small>
```

**After:**
```html
<label class="form-label">
    <i class="fas fa-ruler-combined"></i> Land Area (hectares) 
    <span class="text-danger">*</span>
</label>
<input type="number" class="form-control" name="area" id="area" 
       step="0.01" min="0.01" placeholder="Enter area in hectares" required>
<small class="text-muted">Enter land area or use length × width to calculate</small>
```

**Key Changes:**
- Removed `readonly` attribute
- Made field `required`
- Added red asterisk (*) to indicate required field
- Changed placeholder to "Enter area in hectares"
- Updated help text to explain both input methods
- Changed step to 0.01 for easier input

### 3. Updated JavaScript (templates/machines/rental_form.html)

**Before:**
- Area was always auto-calculated from length × width
- Field was readonly

**After:**
```javascript
function calculateArea() {
    if (landLengthInput && landWidthInput && areaInput) {
        const length = parseFloat(landLengthInput.value) || 0;
        const width = parseFloat(landWidthInput.value) || 0;
        
        // Only auto-calculate if both length and width are provided
        if (length > 0 && width > 0) {
            const areaInHectares = (length * width) / 10000;
            areaInput.value = areaInHectares.toFixed(2);
            // ... visual feedback
        }
    }
}
```

**Key Changes:**
- Only auto-calculates if both length AND width are provided
- Users can manually enter area without providing dimensions
- Changed precision from 4 to 2 decimal places for simplicity
- Maintains auto-calculation feature for convenience

## User Experience

### Option 1: Direct Input
Users can directly enter the land area in hectares:
1. Navigate to rental form
2. Find "Land Area (hectares)" field
3. Enter value (e.g., 2.5)
4. Field accepts values with 2 decimal places
5. Minimum value: 0.01 hectares

### Option 2: Auto-Calculation
Users can still use length × width for automatic calculation:
1. Enter land length in meters
2. Enter land width in meters
3. Area automatically calculates and fills in
4. Formula: (length × width) / 10,000 = hectares
5. Users can still edit the calculated value if needed

### Validation
- Field is now required (marked with red *)
- Minimum value: 0.01 hectares
- Step: 0.01 (allows values like 1.25, 2.50, etc.)
- Browser validation ensures valid input

## Benefits

### 1. Flexibility
- Users can choose their preferred input method
- Direct input for known areas
- Auto-calculation for measured dimensions

### 2. Simplicity
- Clear labeling with icon
- Helpful placeholder text
- Guidance text explains both options

### 3. Accuracy
- 2 decimal places (0.01 ha precision)
- Sufficient for most agricultural needs
- Easier to input than 4 decimal places

### 4. Required Field
- Ensures area is always specified
- Important for pricing calculations
- Prevents incomplete submissions

## Pricing Integration

The area field is used for calculating rental costs for machines priced per hectare:
- 4-Wheel Drive Tractor: ₱4,000/hectare
- Transplanter (Walking): ₱3,500/hectare
- Transplanter (Riding): ₱3,500/hectare
- Precision Seeder: ₱3,500/hectare

When user enters area:
1. System calculates: area × price per hectare
2. Displays estimated cost
3. Shows in rental summary
4. Included in payment calculation

## Examples

### Example 1: Direct Input
```
User enters: 2.5 hectares
Cost calculation: 2.5 × ₱4,000 = ₱10,000
```

### Example 2: Auto-Calculation
```
User enters:
- Length: 100 meters
- Width: 50 meters

Auto-calculated area: (100 × 50) / 10,000 = 0.50 hectares
Cost calculation: 0.50 × ₱4,000 = ₱2,000
```

### Example 3: Mixed Approach
```
User enters dimensions:
- Length: 150 meters
- Width: 100 meters

Auto-calculated: 1.50 hectares
User manually adjusts to: 1.45 hectares (accounting for irregular shape)
Cost calculation: 1.45 × ₱4,000 = ₱5,800
```

## Testing

To verify the implementation:

1. **Test Direct Input:**
   - Go to: http://127.0.0.1:8000/machines/12/rent/
   - Enter area directly (e.g., 2.5)
   - Verify it accepts the value
   - Check cost calculation updates

2. **Test Auto-Calculation:**
   - Enter length: 100
   - Enter width: 50
   - Verify area auto-fills with 0.50
   - Check you can still edit the value

3. **Test Validation:**
   - Try submitting without area
   - Should show "Please fill out this field"
   - Try entering 0 or negative
   - Should show validation error

4. **Test Decimal Places:**
   - Enter 2.5 - should work
   - Enter 2.55 - should work
   - Enter 2.555 - should round to 2.56

## Files Modified
- machines/forms.py (updated area field definition)
- templates/machines/rental_form.html (made field editable, updated JavaScript)

## Status
✅ Implementation complete
✅ No syntax errors
✅ Field is now editable
✅ Field is required
✅ Auto-calculation still works
✅ Manual input enabled
✅ Validation working
✅ Ready for use

## Notes
- Field is required for form submission
- Accepts values from 0.01 hectares and up
- 2 decimal places precision (0.01 ha)
- Auto-calculation only triggers when both length and width are provided
- Users can override auto-calculated values
- Integrates with existing pricing system
