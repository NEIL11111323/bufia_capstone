# Rice Mill Pricing Page Fix

## Summary
Fixed the rice mill pricing page at `/machines/rice-mill-appointments/pricing/` to:
1. Hide the "After Harvest" payment option (settlement_type field)
2. Force rice mill to use immediate cash payment only
3. Update the section description to be specific for rice mill

## Changes Made

### 1. Machine Form Template (`templates/machines/machine_form.html`)

#### JavaScript Update
Updated the `syncPaymentConfigUI()` function to hide rental_price_type and settlement_type fields for rice mill:

**Before:**
- Only dryers had these fields hidden
- Rice mill showed "After Harvest" option

**After:**
- Both dryers AND rice mill have these fields hidden
- Rice mill is forced to use cash payment with immediate settlement
- Added `isRiceMill` check alongside `isDryer` check

```javascript
const isRiceMill = machineTypeValue === 'rice_mill';
// Hide rental_price_type and settlement_type for dryers and rice mill
if (rentalPriceTypeGroup) rentalPriceTypeGroup.style.display = (isDryer || isRiceMill) ? 'none' : '';
if (settlementTypeGroup) settlementTypeGroup.style.display = (isDryer || isRiceMill) ? 'none' : '';
```

#### Section Description Update
Updated the pricing section description to be context-aware:

```html
<p class="section-note">
    {% if is_ricemill_pricing_flow %}
    Configure the rice mill service pricing. Rice mill uses immediate cash payment only.
    {% else %}
    Configure how this machine will be settled: regular cash rate or non-cash payment after harvest.
    {% endif %}
</p>
```

### 2. Machine Form (`machines/forms.py`)

#### Clean Method Update
Added rice mill validation to force cash payment and immediate settlement:

```python
# Force rice mill to use cash payment and immediate settlement
if machine_type == 'rice_mill':
    cleaned_data['rental_price_type'] = 'cash'
    cleaned_data['settlement_type'] = 'immediate'
    cleaned_data['pricing_unit'] = pricing_unit or 'kg'
```

#### Save Method Update
Added rice mill handling in the save method:

```python
# Force rice mill to use cash payment and immediate settlement
if machine.machine_type == 'rice_mill':
    machine.rental_price_type = 'cash'
    machine.settlement_type = 'immediate'
    price_amount = Decimal(str(self.cleaned_data.get('current_price') or '0')).quantize(Decimal('0.01'))
    pricing_unit = self.cleaned_data.get('pricing_unit') or 'kg'
    machine.current_price = f"{price_amount}/{pricing_unit}"
    machine.rental_fee_per_day = price_amount
```

## Technical Details

### Field Visibility Logic
The form now hides the following fields for rice mill:
- `rental_price_type` (Fixed Rate vs Non-cash payment)
- `settlement_type` (Immediate vs After Harvest)

These fields are automatically set to:
- `rental_price_type`: 'cash'
- `settlement_type`: 'immediate'

### Pricing Unit
Rice mill defaults to 'kg' (per kilogram) as the pricing unit, which is appropriate for rice milling services.

## User Experience

### Before:
- Admin could see "After Harvest" option for rice mill
- Could accidentally set rice mill to non-cash payment
- Confusing options that don't apply to rice mill service

### After:
- Clean interface showing only relevant fields
- Clear message: "Rice mill uses immediate cash payment only"
- No confusing "After Harvest" option
- Automatic enforcement of correct payment settings

## Testing Recommendations

1. **Access the rice mill pricing page:**
   - Navigate to `/machines/rice-mill-appointments/pricing/`
   - Verify "Settlement Type" field is hidden
   - Verify "Rental Price Type" field is hidden
   - Verify section description mentions "immediate cash payment only"

2. **Update rice mill pricing:**
   - Change the price amount
   - Save the form
   - Verify the rice mill is saved with:
     - `rental_price_type` = 'cash'
     - `settlement_type` = 'immediate'

3. **Check other machine types:**
   - Edit a tractor or harvester
   - Verify "Settlement Type" field is still visible
   - Verify "After Harvest" option is available for appropriate machines

## Benefits

✅ **Cleaner UI:** No irrelevant fields for rice mill  
✅ **Prevents Errors:** Can't accidentally set wrong payment type  
✅ **Clear Messaging:** Explicit about rice mill payment requirements  
✅ **Consistent Behavior:** Rice mill always uses immediate cash payment  
✅ **Better UX:** Admins see only what they need to configure
