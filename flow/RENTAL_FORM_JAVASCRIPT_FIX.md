# Rental Form JavaScript Fix - Machine Type Not Updating

## Problem

When selecting a machine from the dropdown, the machine type and related fields don't update properly.

## Root Cause

The `machine-data` div is only populated on page load with the pre-selected machine. When user changes the machine selection, the data attributes aren't updated.

## Solution

Add JavaScript to update all machine-related data when selection changes.

## Fix to Apply

Add this JavaScript to `templates/machines/rental_form.html` after line 935:

```javascript
// Machine selection handler - UPDATE THIS SECTION
const machineSelect = document.getElementById('machine_select');
if (machineSelect) {
    machineSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption && selectedOption.value) {
            // Get machine data from selected option
            const machineName = selectedOption.dataset.name || '';
            const machineType = selectedOption.dataset.type || '';
            const machinePrice = selectedOption.dataset.price || '0';
            
            console.log('Selected machine:', machineName, 'Type:', machineType);
            
            // Update machine-data div
            const machineDataEl = document.getElementById('machine-data');
            if (machineDataEl) {
                machineDataEl.dataset.name = machineName;
                machineDataEl.dataset.type = machineType;
                machineDataEl.dataset.price = machinePrice;
            }
            
            // Update service type dropdown
            const serviceTypeSelect = document.getElementById('service_type_select');
            if (serviceTypeSelect) {
                // Try to find matching option
                let foundOption = false;
                for (let i = 0; i < serviceTypeSelect.options.length; i++) {
                    if (serviceTypeSelect.options[i].text.toLowerCase().includes(machineName.toLowerCase())) {
                        serviceTypeSelect.selectedIndex = i;
                        foundOption = true;
                        break;
                    }
                }
                if (!foundOption) {
                    serviceTypeSelect.selectedIndex = 0; // Select first option
                }
            }
            
            // Update rate display based on machine type
            const rateDisplay = document.getElementById('rate_display');
            if (rateDisplay) {
                let rateText = '';
                
                if (machineType === 'rice_mill' || machineType === 'flatbed_dryer') {
                    rateText = '₱150/hour';
                } else if (machineType === 'tractor_4wd') {
                    rateText = '₱4,000/hectare';
                } else if (machineType === 'hand_tractor') {
                    rateText = '₱' + machinePrice + ' flat fee';
                } else if (machineType === 'transplanter_walking' || machineType === 'transplanter_riding' || machineType === 'precision_seeder') {
                    rateText = '₱3,500/hectare';
                } else if (machineType === 'harvester') {
                    rateText = '1 sack per 9 sacks harvested';
                } else {
                    rateText = '₱' + machinePrice + '/day';
                }
                
                rateDisplay.textContent = rateText;
            }
            
            // Show/hide land dimensions based on machine type
            const landDimensionsSection = document.getElementById('land-dimensions-section');
            if (landDimensionsSection) {
                if (machineType === 'tractor_4wd' || machineType === 'hand_tractor' || 
                    machineType === 'harvester' || machineType === 'transplanter_walking' ||
                    machineType === 'transplanter_riding' || machineType === 'precision_seeder') {
                    landDimensionsSection.style.display = 'block';
                } else {
                    landDimensionsSection.style.display = 'none';
                }
            }
            
            // Recalculate cost
            if (typeof calculateCost === 'function') {
                calculateCost();
            }
        }
    });
}
```

## Complete Fixed JavaScript Section

Replace the entire machine selection handler (lines 920-940) with:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Get tomorrow's date for date validation
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    // Machine selection handler - FIXED VERSION
    const machineSelect = document.getElementById('machine_select');
    if (machineSelect) {
        machineSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                // Get machine data from selected option
                const machineName = selectedOption.dataset.name || '';
                const machineType = selectedOption.dataset.type || '';
                const machinePrice = selectedOption.dataset.price || '0';
                
                console.log('Machine changed:', machineName, 'Type:', machineType, 'Price:', machinePrice);
                
                // Update machine-data div with new values
                const machineDataEl = document.getElementById('machine-data');
                if (machineDataEl) {
                    machineDataEl.dataset.name = machineName;
                    machineDataEl.dataset.type = machineType;
                    machineDataEl.dataset.price = machinePrice;
                    console.log('Updated machine-data:', machineDataEl.dataset);
                }
                
                // Update service type dropdown
                const serviceTypeSelect = document.getElementById('service_type_select');
                if (serviceTypeSelect) {
                    let foundOption = false;
                    for (let i = 0; i < serviceTypeSelect.options.length; i++) {
                        const optionText = serviceTypeSelect.options[i].text.toLowerCase();
                        if (optionText.includes(machineName.toLowerCase()) || 
                            machineName.toLowerCase().includes(optionText)) {
                            serviceTypeSelect.selectedIndex = i;
                            foundOption = true;
                            console.log('Matched service type:', serviceTypeSelect.options[i].text);
                            break;
                        }
                    }
                    if (!foundOption) {
                        console.log('No matching service type found for:', machineName);
                    }
                }
                
                // Update rate display
                updateRateDisplay(machineType, machinePrice, machineName);
                
                // Show/hide land dimensions
                updateLandDimensionsVisibility(machineType);
                
                // Recalculate cost if function exists
                if (typeof calculateCost === 'function') {
                    calculateCost();
                }
            }
        });
    }
    
    // Helper function to update rate display
    function updateRateDisplay(machineType, machinePrice, machineName) {
        const rateDisplay = document.getElementById('rate_display');
        if (!rateDisplay) return;
        
        let rateText = '';
        
        // Check by machine type
        if (machineType === 'rice_mill' || machineType === 'flatbed_dryer' || 
            machineName.toLowerCase().includes('rice mill') || 
            machineName.toLowerCase().includes('flatbed dryer')) {
            rateText = '₱150/hour';
        } else if (machineType === 'tractor_4wd' || 
                   machineName.toLowerCase().includes('4wheel') || 
                   machineName.toLowerCase().includes('4wd')) {
            rateText = '₱4,000/hectare';
        } else if (machineType === 'hand_tractor' || 
                   machineName.toLowerCase().includes('hand tractor')) {
            rateText = '₱' + machinePrice + ' flat fee';
        } else if (machineType === 'transplanter_walking' || 
                   machineType === 'transplanter_riding' || 
                   machineType === 'precision_seeder' ||
                   machineName.toLowerCase().includes('transplanter') ||
                   machineName.toLowerCase().includes('seeder')) {
            rateText = '₱3,500/hectare';
        } else if (machineType === 'harvester' || 
                   machineName.toLowerCase().includes('harvester')) {
            rateText = '1 sack per 9 sacks harvested';
        } else {
            rateText = '₱' + machinePrice + '/day';
        }
        
        rateDisplay.textContent = rateText;
        console.log('Updated rate display:', rateText);
    }
    
    // Helper function to show/hide land dimensions
    function updateLandDimensionsVisibility(machineType) {
        const landDimensionsSection = document.getElementById('land-dimensions-section');
        if (!landDimensionsSection) return;
        
        const showForTypes = [
            'tractor_4wd', 
            'hand_tractor', 
            'harvester', 
            'transplanter_walking',
            'transplanter_riding', 
            'precision_seeder'
        ];
        
        if (showForTypes.includes(machineType)) {
            landDimensionsSection.style.display = 'block';
            console.log('Showing land dimensions for:', machineType);
        } else {
            landDimensionsSection.style.display = 'none';
            console.log('Hiding land dimensions for:', machineType);
        }
    }
    
    // Rest of the code continues...
```

## Testing

1. Open rental form
2. Select different machines from dropdown
3. Check console for logs
4. Verify:
   - Rate display updates
   - Service type updates
   - Land dimensions show/hide correctly
   - Cost calculation updates

## Files to Modify

- `templates/machines/rental_form.html` (lines 920-940)

---

**Fix Status**: ⏳ READY TO APPLY  
**Impact**: Machine type and related fields will update properly when selection changes  
**Date**: December 2, 2024
