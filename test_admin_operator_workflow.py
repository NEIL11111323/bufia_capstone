"""
Test script to verify complete admin-operator workflow for IN-KIND rentals
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia_project.settings')
django.setup()

from machines.models import Rental
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("ADMIN-OPERATOR WORKFLOW TEST FOR IN-KIND RENTALS")
print("=" * 80)

# Find IN-KIND rentals at different stages
in_kind_rentals = Rental.objects.filter(
    payment_type='in_kind'
).select_related('machine', 'user', 'assigned_operator').order_by('-created_at')

print(f"\n✅ Found {in_kind_rentals.count()} IN-KIND rental(s)\n")

# Group by workflow state
workflow_stages = {
    'pending': [],
    'approved': [],
    'in_progress': [],
    'harvest_reported': [],
    'waiting_delivery': [],
    'completed': []
}

for rental in in_kind_rentals:
    if rental.status == 'pending':
        workflow_stages['pending'].append(rental)
    elif rental.status == 'approved' and rental.workflow_state == 'approved':
        workflow_stages['approved'].append(rental)
    elif rental.workflow_state == 'in_progress':
        workflow_stages['in_progress'].append(rental)
    elif rental.operator_status == 'harvest_reported':
        workflow_stages['harvest_reported'].append(rental)
    elif rental.settlement_status == 'waiting_for_delivery':
        workflow_stages['waiting_delivery'].append(rental)
    elif rental.status == 'completed':
        workflow_stages['completed'].append(rental)

print("\n" + "=" * 80)
print("WORKFLOW STAGES BREAKDOWN")
print("=" * 80)

for stage, rentals in workflow_stages.items():
    if rentals:
        print(f"\n📍 {stage.upper().replace('_', ' ')} ({len(rentals)} rental(s)):")
        for rental in rentals[:3]:  # Show first 3
            print(f"   • Rental #{rental.id} - {rental.machine.name}")
            print(f"     Renter: {rental.user.get_full_name()}")
            print(f"     Status: {rental.get_status_display()}")
            print(f"     Workflow State: {rental.workflow_state}")
            print(f"     Operator Status: {rental.get_operator_status_display()}")
            if rental.assigned_operator:
                print(f"     Operator: {rental.assigned_operator.get_full_name()}")
            if rental.settlement_status:
                print(f"     Settlement: {rental.get_settlement_status_display()}")
            print(f"     URL: /machines/admin/rental/{rental.id}/approve/")
            print()

print("\n" + "=" * 80)
print("COMPLETE IN-KIND WORKFLOW FOR ADMIN")
print("=" * 80)
print("""
STEP 1: APPROVE & ASSIGN OPERATOR (Status: pending)
   → Admin reviews rental request
   → Admin assigns operator from dropdown
   → Admin approves rental
   → Status changes to: approved
   → Operator receives notification

STEP 2: START EQUIPMENT OPERATION (Status: approved)
   → Admin clicks "Start Equipment Operation" button
   → Workflow state changes to: in_progress
   → Operator can begin work
   → Machine status updates

STEP 3: OPERATOR COMPLETES WORK (Status: in_progress)
   → Operator updates status via their dashboard
   → Operator submits harvest data (total sacks)
   → System auto-calculates BUFIA share using ratio
   → Settlement status changes to: waiting_for_delivery
   → Member receives notification about rice delivery requirement

STEP 4: ADMIN CONFIRMS RICE DELIVERY (Settlement: waiting_for_delivery)
   → Admin sees rice confirmation form
   → Admin enters sacks received
   → Admin clicks "Confirm Rice Delivery & Complete Rental"
   → Settlement status changes to: paid
   → Rental status changes to: completed
   → Member receives completion notification

STEP 5: COMPLETED (Status: completed)
   → Rental is fully completed
   → Machine becomes available
   → Settlement reference generated
   → Transaction reference generated
""")

print("=" * 80)
print("ADMIN ACTIONS AVAILABLE IN APPROVAL PAGE")
print("=" * 80)
print("""
1. Assign Operator (for pending rentals)
2. Approve/Reject Decision
3. Start Equipment Operation (for approved IN-KIND rentals)
4. Record Harvest Report (if operator hasn't submitted)
5. Confirm Rice Delivery (when waiting for delivery)
6. View Operator Status & Notes
""")

print("\n" + "=" * 80)
print("KEY FIELDS TO MONITOR")
print("=" * 80)
print("""
• status: pending → approved → completed
• workflow_state: requested → approved → in_progress → harvest_report_submitted → completed
• operator_status: unassigned → assigned → traveling → operating → harvest_reported
• settlement_status: to_be_determined → pending → waiting_for_delivery → paid
• payment_status: pending → paid_in_kind
""")

print("\n" + "=" * 80)
