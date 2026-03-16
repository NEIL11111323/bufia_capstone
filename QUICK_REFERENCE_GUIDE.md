# Quick Reference Guide - Membership Dashboard

## 🎯 Quick Access
**Dashboard URL:** `/users/` or click "Users Management" in admin menu

## 📊 Dashboard Sections (Top to Bottom)

### 1️⃣ Statistics Cards (Top Row)
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Pending    │  Payment    │  Approved   │  Rejected   │
│  Payment    │  Received   │  Members    │             │
│     ##      │     ##      │     ##      │     ##      │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 2️⃣ Payment Received (BLUE) - PRIORITY SECTION
**This is where you take action!**
- Applications that have paid ₱500
- Ready for approval
- **Action:** Click "Approve Membership"

### 3️⃣ Pending Payment (YELLOW)
- Applications waiting for payment
- **Action:** Click "Mark as Paid" when payment received

### 4️⃣ Approved Members (GREEN)
- Verified and active members
- Can rent machines
- **Status:** Complete

### 5️⃣ Rejected Applications (RED)
- Applications that were rejected
- **Status:** Must reapply

## 🔢 Transaction ID Format
```
BUFIA-MEM-00001
BUFIA-MEM-00042
BUFIA-MEM-00123
```
- Always 5 digits
- Unique for each application
- Use for tracking and reference

## ⚡ Quick Actions

### Mark Payment as Paid (Face-to-Face)
```
1. Find in "Pending Payment" section
2. Click "Mark as Paid"
3. Verify details
4. Confirm
→ Moves to "Payment Received"
```

### Approve Membership
```
1. Find in "Payment Received" section
2. Click "Approve Membership"
3. Select sector
4. Confirm
→ User becomes verified
```

### Reject Application
```
1. Click "Reject" button
2. Enter reason
3. Confirm
→ Moves to "Rejected"
```

## 🚫 Common Errors

### "Cannot verify - payment not received"
**Fix:** Mark payment as paid first, then approve

### User can't rent after approval
**Check:**
- Is payment status "paid"? ✓
- Is user verified? ✓
- Is application approved? ✓

## 📱 Notifications Sent

### When you mark as paid:
- ✉️ User: "Payment confirmed (Transaction ID: BUFIA-MEM-XXXXX)"

### When you approve:
- ✉️ User: "Membership approved (Transaction ID: BUFIA-MEM-XXXXX)"

### When payment received online:
- ✉️ You: "Payment received from [NAME] (Transaction ID: BUFIA-MEM-XXXXX)"

## 🎨 Color Guide
- 🟨 **Yellow** = Waiting for payment
- 🟦 **Blue** = Payment received, needs approval
- 🟩 **Green** = Approved and verified
- 🟥 **Red** = Rejected

## ⏱️ Daily Workflow

### Morning Routine:
1. Check blue "Payment Received" section
2. Approve all paid applications
3. Assign sectors
4. Check yellow "Pending Payment" section
5. Follow up if needed

### When Member Visits Office:
1. Receive ₱500 cash
2. Go to dashboard
3. Find their application in "Pending Payment"
4. Click "Mark as Paid"
5. Confirm transaction ID
6. Then approve membership

## 🔑 Key Rules

1. **Payment First, Approval Second**
   - Cannot approve without payment
   - System enforces this

2. **Transaction ID Always Visible**
   - In dashboard
   - In notifications
   - On confirmation pages

3. **Sector Required**
   - Must assign sector when approving
   - Can update later if needed

4. **Non-Verified Users**
   - Can view everything
   - Cannot rent machines
   - Get notification when they try

## 📞 Quick Support

### If application not showing:
- Check if form was submitted
- Look in all sections
- Search by name or email

### If payment not updating:
- Refresh page
- Check payment status in application details
- Verify transaction ID

### If user still can't rent:
- Verify payment status = "paid"
- Verify user.is_verified = True
- Verify application.is_approved = True

## 💡 Pro Tips

1. **Use Transaction IDs** when communicating with members
2. **Process blue section first** - these are ready to go
3. **Assign correct sector** - based on farm location
4. **Check payment method** - online vs face-to-face
5. **Keep notes** in rejection reasons

## 📋 Checklist for Approval

Before clicking "Approve Membership":
- [ ] Payment status shows "paid"
- [ ] Transaction ID is visible
- [ ] Member information is complete
- [ ] Correct sector selected
- [ ] Ready to confirm

## 🎯 Success Indicators

Application successfully processed when:
- ✅ User receives approval notification
- ✅ User can create rental requests
- ✅ Application shows in "Approved Members"
- ✅ Transaction ID recorded

---

**Remember:** Blue section = Action needed! Process these first.
