# BUFIA Complete System Flow

## 🎯 OVERALL WORKFLOW

```
ADMIN → Create Rental → Assign Operator → Monitor
   ↓
OPERATOR → Receive → Start → Ongoing → Complete
   ↓
ADMIN → Verify → Finalize → Record
```

## 👨‍💼 ADMIN WORKFLOW

### 1. Create Rental Request
- **URL**: `/machines/admin/rentals/`
- **Actions**:
  - Enter farmer details
  - Select machine
  - Set schedule
  - **Status**: `pending`

### 2. Assign Operator
- **URL**: `/machines/admin/rental/<id>/assign/`
- **Actions**:
  - Select operator from list
  - Assign to rental
  - **Status**: `pending` → `assigned`
  - **Notification**: Operator receives notification

### 3. Monitor Jobs
- **URL**: `/dashboard/`
- **View**:
  - Assigned jobs
  - Ongoing jobs
  - Completed jobs
  - Job statistics

### 4. Verify & Finalize
- **URL**: `/machines/admin/rental/<id>/`
- **Actions**:
  - Review completion details
  - Verify work done
  - Mark as finalized
  - **Status**: `completed` → `finalized`

---

## 🧑‍🔧 OPERATOR WORKFLOW

### 1. Receive Assigned Job
- **URL**: `/machines/operator/jobs/`
- **View**: List of assigned jobs
- **Status**: `assigned`

### 2. Start Job
- **URL**: `/machines/operator/rental/<id>/start/`
- **Validation**:
  - ✅ Check if operator has ongoing job
  - ❌ Block if already has ongoing job
- **Actions**:
  - Click "Start Job"
  - **Status**: `assigned` → `ongoing`
  - Record start time
- **Notification**: Admin receives notification

### 3. Job Ongoing
- **URL**: `/machines/operator/`
- **View**:
  - Current ongoing job
  - Job details
  - Start time
  - "Complete Job" button

### 4. Complete Job
- **URL**: `/machines/operator/rental/<id>/complete/`
- **Actions**:
  - Click "Complete Job"
  - Enter output/notes (optional)
  - **Status**: `ongoing` → `completed`
  - Record end time & duration
- **Notification**: Admin receives notification

---

## 📊 STATUS FLOW

| Status | Who Controls | Meaning | Next Action |
|--------|-------------|---------|-------------|
| `pending` | Admin | Rental created | Assign operator |
| `assigned` | Admin | Operator assigned | Operator starts |
| `ongoing` | Operator | Work in progress | Operator completes |
| `completed` | Operator | Work finished | Admin verifies |
| `finalized` | Admin | Approved & recorded | Closed |

---

## 🔐 BUSINESS RULES

### Operator Constraints
1. ✅ **ONE ONGOING JOB RULE**
   - Operator can only have 1 ongoing job at a time
   - Enforced when starting a job
   - Must complete current job before starting new one

2. ✅ **Job Assignment**
   - Admin can assign multiple jobs to operator
   - Jobs queue in "Assigned" status
   - Operator activates them one by one

### Admin Capabilities
1. ✅ **Unlimited Assignments**
   - Can assign multiple jobs to same operator
   - Can reassign jobs to different operators
   - Can view all operator statuses

2. ✅ **Monitoring**
   - Real-time job status
   - Operator performance metrics
   - Completion history

---

## 🔗 DATABASE CONNECTIONS

### Rental Model
```python
class Rental:
    user = ForeignKey(User)  # Farmer
    machine = ForeignKey(Machine)
    operator = ForeignKey(User, role='operator')  # Assigned operator
    status = CharField(choices=[
        'pending', 'assigned', 'ongoing', 
        'completed', 'finalized'
    ])
    start_time = DateTimeField()
    end_time = DateTimeField()
```

### Key Relationships
- `Rental.operator` → Links to operator user
- `Rental.status` → Tracks workflow stage
- `Rental.start_time/end_time` → Records duration

---

## 📱 NOTIFICATIONS

### Admin Receives
- ✉️ Operator started job
- ✉️ Operator completed job
- ✉️ Job requires verification

### Operator Receives
- ✉️ New job assigned
- ✉️ Job deadline approaching
- ✉️ Job verified by admin

---

## 🎨 UI SECTIONS

### Admin Dashboard
- **Pending Rentals**: Awaiting assignment
- **Assigned Jobs**: Operators assigned
- **Ongoing Jobs**: Currently in progress
- **Completed Jobs**: Awaiting verification
- **Finalized Jobs**: Closed & recorded

### Operator Dashboard
- **Assigned Jobs**: Queue of jobs to do
- **Current Job**: Ongoing work (max 1)
- **Completed Jobs**: Finished work history

---

## ✅ DEPLOYMENT CHECKLIST

- [x] Setup page created (`/setup/`)
- [x] Admin can create rentals
- [x] Admin can assign operators
- [x] Operator can view assigned jobs
- [x] Operator can start jobs (with validation)
- [x] Operator can complete jobs
- [x] Admin can verify completed jobs
- [x] Notifications system working
- [x] One ongoing job rule enforced
- [x] Status transitions working

---

## 🚀 QUICK START

### For Fresh Deployment
1. Visit `/setup/` to create admin account
2. Login as admin
3. Create operators in user management
4. Create machines
5. Start creating rentals!

### For Testing
1. **As Admin**: Create rental → Assign operator
2. **As Operator**: Start job → Complete job
3. **As Admin**: Verify → Finalize

---

## 📞 SUPPORT

All workflows are now deployed and functional on:
**https://bufia-capstone.onrender.com**

Admin setup: `/setup/`
Admin login: `/accounts/login/`
Dashboard: `/dashboard/`
