# IN-KIND Workflow - Verification Commands

Use these commands to verify the implementation is working correctly.

---

## 1. System Check

Verify Django system is healthy:

```bash
python manage.py check
```

**Expected Output**:
```
System check identified no issues (0 silenced).
```

---

## 2. Run All Tests

Run all in-kind workflow tests:

```bash
python manage.py test tests.test_in_kind_workflow tests.test_in_kind_properties_simple -v 2
```

**Expected Output**:
```
Ran 44 tests in ~24s
OK
```

---

## 3. Run Unit Tests Only

Run only the unit tests:

```bash
python manage.py test tests.test_in_kind_workflow -v 2
```

**Expected Output**:
```
Ran 31 tests in ~15s
OK
```

---

## 4. Run Property-Based Tests Only

Run only the property-based tests:

```bash
python manage.py test tests.test_in_kind_properties_simple -v 2
```

**Expected Output**:
```
Ran 13 tests in ~8s
OK
```

---

## 5. Run Specific Property Test

Test the BUFIA share calculation invariant:

```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_6_bufia_share_calculation_invariant -v 2
```

**Expected Output**:
```
test_property_6_bufia_share_calculation_invariant ... ok
Ran 1 test in ~0.5s
OK
```

---

## 6. Run All Tests with Coverage

Run tests with coverage report:

```bash
coverage run --source='machines' manage.py test tests.test_in_kind_workflow tests.test_in_kind_properties_simple
coverage report
```

**Expected Output**:
```
Name                          Stmts   Miss  Cover
-----------------------------------------------
machines/models.py              XXX    XX   XX%
machines/utils.py               XXX    XX   XX%
machines/admin_views.py         XXX    XX   XX%
-----------------------------------------------
TOTAL                           XXX    XX   XX%
```

---

## 7. Verify Database Migrations

Check that all migrations are applied:

```bash
python manage.py showmigrations machines
```

**Expected Output** (should show all migrations with [X]):
```
machines
 [X] 0001_initial
 [X] 0002_alter_machine_current_price
 ...
 [X] 0010_add_in_kind_workflow
 [X] 0011_add_state_changed_fields
 [X] 0012_add_actual_completion_time
```

---

## 8. Verify Models

Check that all models are properly defined:

```bash
python manage.py inspectdb machines | grep -E "class (Rental|HarvestReport|Settlement|RentalStateChange)"
```

**Expected Output**:
```
class Rental(models.Model):
class HarvestReport(models.Model):
class Settlement(models.Model):
class RentalStateChange(models.Model):
```

---

## 9. Test Individual Properties

### Property 1: Rental Request Creation
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_1_rental_request_creation_basic -v 2
```

### Property 2: Admin Approval
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_2_admin_approval_transitions -v 2
```

### Property 3: Admin Rejection
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_3_admin_rejection_cancels -v 2
```

### Property 4: Equipment Operation
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_4_equipment_operation_tracking -v 2
```

### Property 5: Harvest Report Recording
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_5_harvest_report_recording_various_amounts -v 2
```

### Property 6: BUFIA Share Calculation
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_6_bufia_share_calculation_invariant -v 2
```

### Property 7: Harvest Verification
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_7_harvest_verification_creates_settlement -v 2
```

### Property 8: Harvest Rejection
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_8_harvest_rejection_reverts_state -v 2
```

### Property 9: Rental Validation
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_9_rental_validation_rejects_invalid_data -v 2
```

### Property 10: Harvest Data Validation
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_10_harvest_validation_rejects_invalid_sacks -v 2
```

### Property 11: Audit Trail
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_11_audit_trail_completeness -v 2
```

### Property 12: Notifications
```bash
python manage.py test tests.test_in_kind_properties_simple.PropertyBasedTestsSimplified.test_property_12_notification_delivery_for_events -v 2
```

---

## 10. Quick Verification Script

Run this script to verify everything:

```bash
#!/bin/bash

echo "=== Django System Check ==="
python manage.py check

echo ""
echo "=== Running All Tests ==="
python manage.py test tests.test_in_kind_workflow tests.test_in_kind_properties_simple -v 1

echo ""
echo "=== Verification Complete ==="
```

---

## Expected Results

All commands should complete successfully with:
- ✅ No errors
- ✅ No warnings
- ✅ All tests passing
- ✅ All migrations applied

---

## Troubleshooting

### If tests fail:

1. **Check database**: `python manage.py migrate`
2. **Check imports**: `python manage.py shell` then `from machines.models import Rental, HarvestReport, Settlement, RentalStateChange`
3. **Check utilities**: `python manage.py shell` then `from machines.utils import create_rental_request, approve_rental, etc.`

### If migrations fail:

```bash
python manage.py migrate machines
python manage.py migrate
```

### If specific test fails:

Run with verbose output:
```bash
python manage.py test tests.test_in_kind_workflow -v 3
```

---

## Performance Baseline

Expected test execution times:
- Unit tests (31): ~15 seconds
- Property tests (13): ~8 seconds
- Total (44): ~23 seconds

If tests take significantly longer, check:
- Database performance
- System resources
- Background processes
