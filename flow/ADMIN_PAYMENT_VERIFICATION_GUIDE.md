# Admin Payment Verification Guide

## 🎯 Overview

Admins can now view user payment details and payment slips before approving rental requests.

## 📍 Access Points

### 1. Admin Dashboard
```
URL: /machines/admin/dashboard/
```

**Features:**
- View all rental requests
- Filter by status and payment
- See payment proof thumbnails
- Quick verify payment button
- Bulk approve multiple rentals

### 2. Individual Rental Approval
```
URL: /machines/admin/rental/{id}/approve/
```

**Features:**
- Full rental details
- User information
- Payment information
- **Payment proof viewer** (images and PDFs)
- Conflict detection
- Approval form with admin notes

## 🖼️ Payment Proof Viewing

### For Images (JPG, PNG)
- **Thumbnail preview** in dashboard
- **Full-size view** in approval page
- Click image to open in new tab
- Download button available

### For PDFs
- **PDF icon** in dashboard
- **Open in new tab** button in approval page
- Download button available

## 📋 Approval Workflow

### Step 1: Access Dashboard
```
1. Login as admin
2. Navigate to /machines/admin/dashboard/
3. See list of all rental requests
```

### Step 2: Review Payment
```
1. Click "Review" button on any rental
2. View payment details:
   - Payment method (Online/Face-to-Face)
   - Payment amount
   - Payment date
   - Verification status
3. View payment proof:
   - For images: See full-size preview
   - For PDFs: Click to open in new tab
```

### Step 3: Verify Payment
```
1. Check payment proof matches payment details
2. Check "Verify Payment" checkbox
3. Or use "Quick Verify" button in dashboard
```

### Step 4: Check for Conflicts
```
System automatically checks for conflicts with:
- Other APPROVED rentals
- Maintenance schedules

If conflicts exist:
- Warning message displayed
- Cannot approve until resolved
```

### Step 5: Approve or Reject
```
1. Select decision:
   - Keep Pending
   - Approve Rental
   - Reject Rental

2. Add admin notes (optional)

3. Click "Submit Decision"

4. User gets notification
```

## 🎨 Dashboard Features

### Statistics Cards
```
┌─────────────────────────────────────────────────────┐
│  [12]        [8]         [4]         [10]           │
│  Total     Paid &      Unpaid    With Payment       │
│  Pending   Pending               Proof              │
└─────────────────────────────────────────────────────┘
```

### Filters
- **Status**: All / Pending / Approved / Rejected
- **Payment**: All / Verified / Unverified / With Proof
- **Search**: User name or machine name

### Rental Cards
Each rental shows:
- ✅ Machine name
- ✅ User details
- ✅ Rental dates
- ✅ Payment status badge
- ✅ Payment proof thumbnail/icon
- ✅ Quick actions (Review, Quick Verify)

## 📸 Payment Proof Examples

### Image Payment Proof
```
┌─────────────────────────────────────┐
│                                     │
│     [Payment Receipt Image]         │
│                                     │
│  Click to view full size            │
│                                     │
│  [Open in New Tab] [Download]      │
└─────────────────────────────────────┘
```

### PDF Payment Proof
```
┌─────────────────────────────────────┐
│                                     │
│         📄 PDF Document             │
│                                     │
│     payment_receipt.pdf             │
│                                     │
│  [Open PDF] [Download]              │
└─────────────────────────────────────┘
```

## 🔍 Detailed Approval Page

### Left Column: Rental & Payment Info
```
┌─────────────────────────────────────┐
│ 📋 Rental Information               │
│  - Machine: HARVESTER               │
│  - Renter: John Doe                 │
│  - Dates: Dec 10-15, 2024           │
│  - Status: Pending                  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 💳 Payment Information              │
│  - Method: Face-to-Face             │
│  - Amount: $500                     │
│  - Date: Dec 2, 2024                │
│  - Verified: ⏳ Not Verified        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 📄 Payment Proof                    │
│                                     │
│  [Full-size image or PDF viewer]    │
│                                     │
└─────────────────────────────────────┘
```

### Right Column: Actions & Timeline
```
┌─────────────────────────────────────┐
│ ✅ Admin Actions                    │
│  ☑ Verify Payment                   │
│  Decision: [Approve ▼]              │
│  Notes: [____________]              │
│  [Submit Decision]                  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ⚡ Quick Actions                    │
│  [View Payment Proof]               │
│  [View Machine Details]             │
│  [View Full Rental Details]         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 📅 Activity Timeline                │
│  • Rental Created                   │
│  • Payment Submitted                │
│  • Payment Verified (if done)       │
│  • Rental Approved (if done)        │
└─────────────────────────────────────┘
```

## 🚨 Conflict Warnings

If conflicts detected:
```
┌─────────────────────────────────────────────────────┐
│ ⚠️ Conflict Warning!                                │
│                                                     │
│ This rental conflicts with:                         │
│                                                     │
│ Rental #15 - Jane Smith                            │
│ Dec 12-17, 2024                                    │
│ HARVESTER                                          │
│                                                     │
│ ⚠️ Cannot approve until conflicts are resolved.    │
└─────────────────────────────────────────────────────┘
```

## 💡 Quick Tips

### For Fast Approval
1. Use dashboard filters to show "Paid & Pending"
2. Use "Quick Verify" button for fast payment verification
3. Use bulk approval for multiple rentals

### For Thorough Review
1. Click "Review" to see full details
2. View payment proof carefully
3. Check conflict warnings
4. Add admin notes for record keeping

### Payment Verification Checklist
- [ ] Payment proof uploaded
- [ ] Payment amount matches
- [ ] Payment date is reasonable
- [ ] Payment method is correct
- [ ] No conflicts with other rentals
- [ ] Machine is available
- [ ] User is verified member

## 🔗 Related URLs

| URL | Purpose |
|-----|---------|
| `/machines/admin/dashboard/` | Main admin dashboard |
| `/machines/admin/rental/{id}/approve/` | Approve individual rental |
| `/machines/admin/rental/{id}/payment-proof/` | View payment proof file |
| `/machines/admin/verify-payment/{id}/` | Quick verify (AJAX) |
| `/machines/admin/bulk-approve/` | Bulk approve rentals |
| `/machines/admin/conflicts/` | Conflict report |

## 📱 Mobile Access

The admin dashboard is responsive and works on:
- ✅ Desktop computers
- ✅ Tablets
- ✅ Mobile phones

## 🎓 Training Checklist

For new admins:
- [ ] Access admin dashboard
- [ ] Filter rentals by status
- [ ] View payment proof (image)
- [ ] View payment proof (PDF)
- [ ] Verify payment
- [ ] Check for conflicts
- [ ] Approve a rental
- [ ] Reject a rental
- [ ] Use bulk approval
- [ ] Add admin notes

## 📞 Support

If you encounter issues:
1. Check browser console for errors
2. Verify you have admin permissions
3. Ensure payment proof file exists
4. Check file permissions on server

---

**Guide Version**: 1.0  
**Last Updated**: December 2, 2024  
**Status**: ✅ Ready to Use
