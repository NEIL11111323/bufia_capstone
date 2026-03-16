# IN-KIND Workflow - Remaining Optional Tasks

**Status**: Core feature complete. Optional enhancements listed below.

---

## Task 13: Member Views and Forms (Optional)

### 13.1 Create Rental Request Form
**Status**: ❌ Not Started  
**Effort**: 2-3 hours

Create a ModelForm for members to submit rental requests:

```python
# machines/forms.py
class RentalRequestForm(ModelForm):
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date']
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
            'end_date': DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        # Validate dates
        # Check machine availability
        # Verify member status
```

**Files to Create**:
- `machines/forms.py` - RentalRequestForm
- `machines/views.py` - RentalRequestCreateView
- `templates/machines/rental_request_form.html` - Form template

### 13.2 Create Rental Detail View for Members
**Status**: ❌ Not Started  
**Effort**: 2 hours

Display rental information and workflow state:

```python
class RentalDetailView(LoginRequiredMixin, DetailView):
    model = Rental
    template_name = 'machines/rental_detail.html'
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user)
```

**Features**:
- Display equipment details
- Show rental dates
- Display workflow state
- Show harvest information if available
- Show settlement information if completed

### 13.3 Create Rental List View for Members
**Status**: ❌ Not Started  
**Effort**: 2 hours

List all rentals for logged-in member with filtering:

```python
class RentalListView(LoginRequiredMixin, ListView):
    model = Rental
    template_name = 'machines/rental_list.html'
    paginate_by = 20
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user)
```

**Features**:
- Filter by workflow state
- Sort by date
- Show summary information
- Pagination

---

## Task 14: Checkpoint - Verify Member Interfaces (Optional)

**Status**: ❌ Not Started  
**Effort**: 1 hour

Verification checklist:
- [ ] Member can submit rental request
- [ ] Member can view rental details
- [ ] Member can list all rentals
- [ ] Filtering works correctly
- [ ] Dates display correctly
- [ ] Settlement information shows

---

## Task 17: Integration Tests (Optional)

### 17.1 End-to-End Workflow Integration Test
**Status**: ❌ Not Started  
**Effort**: 3-4 hours

Test complete workflow from request to settlement:

```python
def test_complete_workflow_integration():
    """Test: request → approval → in_progress → harvest → verification → settlement"""
    
    # 1. Member submits request
    rental = create_rental_request(member, machine, start_date, harvest_date)
    assert rental.workflow_state == 'requested'
    
    # 2. Admin approves
    approve_rental(rental, admin)
    assert rental.workflow_state == 'approved'
    
    # 3. Equipment operation begins
    start_equipment_operation(rental, admin)
    assert rental.workflow_state == 'in_progress'
    
    # 4. Harvest reported
    record_harvest_report(rental, 90, admin)
    assert rental.workflow_state == 'harvest_report_submitted'
    
    # 5. Harvest verified
    verify_harvest_report(rental, admin)
    assert rental.workflow_state == 'completed'
    
    # 6. Settlement created
    settlement = Settlement.objects.get(rental=rental)
    assert settlement.bufia_share == 10
    assert settlement.member_share == 80
```

**Test Scenarios**:
- Happy path (complete workflow)
- Rejection at approval stage
- Rejection at harvest verification
- Early completion
- Cancellation at various stages

### 17.2 Error Scenario Integration Tests
**Status**: ❌ Not Started  
**Effort**: 2-3 hours

Test error handling across workflow:

```python
def test_harvest_rejection_and_resubmission():
    """Test: harvest rejected → recount → resubmit → verify"""
    
    # ... setup ...
    
    # Reject harvest
    reject_harvest_report(rental, 'Recount needed', admin)
    assert rental.workflow_state == 'in_progress'
    
    # Resubmit harvest
    record_harvest_report(rental, 95, admin)
    assert rental.workflow_state == 'harvest_report_submitted'
    
    # Verify new harvest
    verify_harvest_report(rental, admin)
    assert rental.workflow_state == 'completed'
```

**Error Scenarios**:
- Invalid state transitions
- Validation errors
- Duplicate operations
- Concurrent modifications

---

## Additional Enhancements (Future)

### Reporting and Analytics
- Settlement reports by date range
- Harvest statistics by machine
- Member payment history
- BUFIA revenue tracking

### Notifications Enhancement
- Email notifications
- SMS alerts
- Notification preferences
- Notification history

### UI/UX Improvements
- Dashboard widgets
- Real-time status updates
- Bulk operations
- Export to CSV/PDF

### Performance Optimization
- Caching for frequently accessed data
- Async task processing
- Database query optimization
- API rate limiting

---

## Implementation Priority

**High Priority** (Recommended):
1. Task 13.1 - Rental request form (enables member functionality)
2. Task 13.2 - Rental detail view (member visibility)
3. Task 17.1 - Integration tests (workflow validation)

**Medium Priority** (Nice to have):
1. Task 13.3 - Rental list view (member convenience)
2. Task 17.2 - Error scenario tests (robustness)
3. Reporting features

**Low Priority** (Future):
1. Notifications enhancement
2. UI/UX improvements
3. Performance optimization

---

## Estimated Effort

| Task | Effort | Priority |
|------|--------|----------|
| 13.1 - Rental form | 2-3h | High |
| 13.2 - Detail view | 2h | High |
| 13.3 - List view | 2h | Medium |
| 14 - Checkpoint | 1h | Medium |
| 17.1 - Integration tests | 3-4h | High |
| 17.2 - Error tests | 2-3h | Medium |
| **Total** | **12-17h** | - |

---

## Notes

- Core workflow is complete and production-ready
- All 12 correctness properties validated
- 44 tests passing (100%)
- Optional tasks enhance user experience and robustness
- Can be implemented incrementally without affecting core functionality
