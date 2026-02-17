# Membership Payment System - Implementation Guide

## Overview
Added a ₱500 membership fee payment system with two payment options:
1. **Online Payment** - Pay via Stripe (credit/debit card)
2. **Face-to-Face Payment** - Pay in person at BUFIA office

## Features Implemented

### 1. Payment Method Selection
- Radio button choice at the bottom of membership form
- Visual cards for each payment option
- Dynamic instructions based on selection
- Icons showing accepted payment methods

### 2. Online Payment (Stripe)
- Secure payment via Stripe Checkout
- Membership fee: ₱500 = $10 USD
- Auto-updates payment status after successful payment
- Redirects back to profile with confirmation

### 3. Face-to-Face Payment
- Marks payment as "pending"
- User prints membership slip
- Brings slip + ₱500 to BUFIA office
- Admin marks as paid after receiving payment

## Files Modified

### 1. `templates/users/submit_membership_form.html`
**Added:**
- Payment method selection section
- Radio buttons for online/face-to-face
- Visual payment option cards
- Dynamic payment instructions
- JavaScript to toggle instructions

### 2. `users/models.py`
**Added to MembershipApplication:**
```python
payment_method = models.CharField(max_length=20, choices=[
    ('online', 'Online Payment'),
    ('face_to_face', 'Face-to-Face Payment'),
], default='face_to_face')

payment_status = models.CharField(max_length=20, choices=[
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('waived', 'Waived'),
], default='pending')

payment_date = models.DateTimeField(null=True, blank=True)
```

### 3. `users/views.py`
**Updated `submit_membership_form()`:**
- Captures payment_method from form
- Sets payment_status based on method
- Redirects to payment page if online
- Redirects to membership slip if face-to-face

### 4. `bufia/views/payment_views.py`
**Added:**
- `create_membership_payment()` - Creates Stripe session
- Updated `payment_success()` - Handles membership payment completion

### 5. `bufia/urls.py`
**Added:**
```python
path('payment/membership/<int:membership_id>/', 
     payment_views.create_membership_payment, 
     name='create_membership_payment'),
```

## User Flow

### Online Payment Flow
```
1. User fills membership form
   ↓
2. Selects "Online Payment"
   ↓
3. Clicks "Submit Application"
   ↓
4. Redirected to Stripe Checkout
   ↓
5. Enters card details (Test: 4242 4242 4242 4242)
   ↓
6. Payment processed
   ↓
7. Redirected back to profile
   ↓
8. Payment status: "Paid"
   ↓
9. Application pending admin approval
```

### Face-to-Face Payment Flow
```
1. User fills membership form
   ↓
2. Selects "Face-to-Face Payment"
   ↓
3. Clicks "Submit Application"
   ↓
4. Redirected to membership slip
   ↓
5. Prints membership slip
   ↓
6. Visits BUFIA office with ₱500
   ↓
7. Admin marks payment as received
   ↓
8. Admin approves membership
```

## Payment Method Cards

### Online Payment Card
```
┌─────────────────────────────────┐
│         🌐 Globe Icon           │
│                                 │
│      Online Payment             │
│                                 │
│  Pay securely with credit/      │
│  debit card via Stripe          │
│                                 │
│  💳 VISA  💳 MC  💳 AMEX        │
└─────────────────────────────────┘
```

### Face-to-Face Card
```
┌─────────────────────────────────┐
│      🤝 Handshake Icon          │
│                                 │
│   Face-to-Face Payment          │
│                                 │
│  Pay in person at BUFIA office  │
│                                 │
│      💵 Cash Icon               │
└─────────────────────────────────┘
```

## Database Migration Required

After implementing these changes, run:

```bash
# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate
```

This will add the payment fields to the MembershipApplication model.

## Testing

### Test Online Payment
1. Go to: `http://localhost:8000/profile/`
2. Click "Submit Membership Application"
3. Fill in all required fields
4. Select "Online Payment"
5. Click "Submit Application"
6. Use test card: `4242 4242 4242 4242`
7. Complete payment
8. ✅ Should redirect to profile
9. ✅ Payment status should be "Paid"

### Test Face-to-Face Payment
1. Go to: `http://localhost:8000/profile/`
2. Click "Submit Membership Application"
3. Fill in all required fields
4. Select "Face-to-Face Payment"
5. Click "Submit Application"
6. ✅ Should redirect to membership slip
7. ✅ Payment status should be "Pending"
8. Print slip and bring to office

## Admin Features

### View Payment Status
In Django Admin:
1. Go to: `/admin/users/membershipapplication/`
2. See payment_method and payment_status columns
3. Filter by payment status
4. Mark face-to-face payments as "Paid" after receiving

### Payment Status Options
- **Pending**: Awaiting payment
- **Paid**: Payment received (online or face-to-face)
- **Waived**: Fee waived by admin (special cases)

## Payment Amount

**Membership Fee: ₱500**
- Converted to USD for Stripe: $10.00
- Can be adjusted in `create_membership_payment()` view

To change the amount:
```python
# In bufia/views/payment_views.py
amount = 1000  # $10.00 in cents
# Change to desired amount (in cents)
```

## Security

### Online Payment
- ✅ Secure via Stripe
- ✅ No card data stored
- ✅ PCI compliant
- ✅ SSL/TLS encryption

### Face-to-Face Payment
- ✅ Admin verification required
- ✅ Receipt/slip provided
- ✅ Manual confirmation in admin panel

## Notifications

### After Online Payment
- User receives: "Payment successful! Your membership fee has been paid."
- Status: Payment marked as "Paid"
- Next: Awaiting admin approval

### After Face-to-Face Selection
- User receives: "Please print the verification slip and present it to a BUFIA administrator along with the ₱500 membership fee."
- Status: Payment marked as "Pending"
- Next: Visit office with payment

## Customization

### Change Membership Fee
Edit `bufia/views/payment_views.py`:
```python
# Current: ₱500 = $10 USD
amount = 1000  # in cents

# To change to ₱1000 = $20 USD
amount = 2000  # in cents
```

### Add More Payment Methods
Edit `users/models.py`:
```python
payment_method = models.CharField(max_length=20, choices=[
    ('online', 'Online Payment'),
    ('face_to_face', 'Face-to-Face Payment'),
    ('bank_transfer', 'Bank Transfer'),  # Add new option
], default='face_to_face')
```

### Change Currency
Edit `bufia/views/payment_views.py`:
```python
'currency': 'usd',  # Change to 'php', 'eur', etc.
```

## Troubleshooting

### Issue: Payment method not saving
**Solution:** Run migrations to add new fields
```bash
python manage.py makemigrations
python manage.py migrate
```

### Issue: Stripe redirect not working
**Solution:** Check URL configuration in `bufia/urls.py`

### Issue: Payment status not updating
**Solution:** Check `payment_success()` view handles 'membership' type

## Summary

✅ **Payment Options**: Online (Stripe) or Face-to-Face
✅ **Membership Fee**: ₱500 ($10 USD)
✅ **Visual Selection**: Card-based UI with icons
✅ **Dynamic Instructions**: Changes based on selection
✅ **Secure Processing**: Stripe for online payments
✅ **Admin Control**: Can mark face-to-face payments as paid
✅ **Status Tracking**: Pending/Paid/Waived options

The membership payment system is now complete and ready to use!

## Next Steps

1. **Run migrations** to add payment fields
2. **Test both payment methods** thoroughly
3. **Train admins** on marking face-to-face payments
4. **Update membership slip** to show payment status
5. **Add payment receipt** for online payments (optional)
