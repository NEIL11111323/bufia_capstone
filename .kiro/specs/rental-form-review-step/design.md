# Design Document

## Overview

This design implements a two-step rental form submission process: (1) Form Entry and (2) Review & Confirmation. The review step allows users to verify all entered information and select their payment method before final submission.

## Architecture

### Flow Diagram
```
User fills form → Click Submit → Review Page (with payment method selection) → Confirm → Save to Database → Confirmation Page
                                      ↓
                                   Edit Button → Return to Form (data preserved)
```

### Components
1. **Rental Form Page** - Existing form with data collection
2. **Review/Confirmation Page** - New intermediate page for review
3. **Payment Method Selection** - Radio buttons for payment choice
4. **Form State Management** - Session/hidden fields to preserve data
5. **Confirmation Page** - Success message with request details

## Components and Interfaces

### 1. Rental Form Modifications
- Change submit button behavior to show review page instead of direct submission
- Store form data in session or pass via POST to review page
- Add validation before showing review page

### 2. Review Page Template (`rental_review.html`)
**Sections:**
- Header with "Review Your Request" title
- Requester Information display
- Equipment Details display
- Rental Period display
- Service Details display
- Cost Breakdown display
- **Payment Method Selection** (new)
  - Radio buttons: "Online Payment" and "Face-to-Face Payment"
  - Helper text for each option
- Action buttons: "Edit" and "Confirm & Submit"

### 3. Payment Method Field
**Database Model Addition:**
```python
class Rental:
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('online', 'Online Payment'),
            ('face_to_face', 'Face-to-Face Payment')
        ],
        default='face_to_face'
    )
```

### 4. View Logic
**rental_create view modifications:**
- If GET request: Show form
- If POST without 'confirm': Show review page with form data
- If POST with 'confirm': Save rental with payment method

## Data Models

### Rental Model Update
```python
# Add to existing Rental model
payment_method = models.CharField(
    max_length=20,
    choices=PAYMENT_METHOD_CHOICES,
    default='face_to_face',
    help_text='Payment method selected by user'
)
```

### Form Data Structure (Session Storage)
```python
{
    'requester_name': str,
    'machine': int,
    'farm_area': str,
    'operator_type': str,
    'start_date': str,
    'end_date': str,
    'service_type': str,
    'area': float,
    'land_length': float,
    'land_width': float,
    # ... other fields
}
```

## Error Handling

1. **Missing Payment Method**: Display error message "Please select a payment method"
2. **Session Expiry**: Redirect to form with message "Session expired, please fill the form again"
3. **Invalid Data**: Return to form with validation errors
4. **Database Error**: Show error page with retry option

## Testing Strategy

### Unit Tests
- Test rental creation with online payment method
- Test rental creation with face-to-face payment method
- Test form data preservation when editing from review page
- Test validation when payment method is not selected

### Integration Tests
- Test complete flow: Form → Review → Confirm → Success
- Test edit flow: Form → Review → Edit → Form (data preserved)
- Test payment method is saved correctly in database

## Implementation Notes

1. Use Django sessions to store form data between form and review pages
2. Add CSRF token to review page form
3. Style review page to match existing BUFIA design
4. Add payment method icons for better UX
5. Ensure mobile responsiveness for review page
