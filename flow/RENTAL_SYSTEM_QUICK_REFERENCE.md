# Machine Rental System - Quick Reference Card

## 🚀 Quick Start

### Check if Machine is Available
```python
from machines.models import Rental
from datetime import date

is_available, conflicts = Rental.check_availability(
    machine=machine,
    start_date=date(2025, 12, 10),
    end_date=date(2025, 12, 15)
)

if is_available:
    print("✅ Machine is available!")
else:
    print(f"❌ Conflicts found: {conflicts.count()}")
```

### Create a Rental (Safe Way)
```python
from django.db import transaction

@transaction.atomic
def create_rental_safe(machine, user, start_date, end_date):
    # Lock the machine
    machine = Machine.objects.select_for_update().get(pk=machine.pk)
    
    # Check availability
    is_available, conflicts = Rental.check_availability(
        machine, start_date, end_date
    )
    
    if not is_available:
        raise ValidationError("Machine not available")
    
    # Create rental
    return Rental.objects.create(
        machine=machine,
        user=user,
        start_date=start_date,
        end_date=end_date,
        status='pending'
    )
```

## 📋 Key Files Modified

| File | What Changed |
|------|-------------|
| `machines/models.py` | Added indexes, constraints, `check_availability()` method |
| `machines/forms.py` | Enhanced validation with 6 rules |
| `machines/views_optimized.py` | New transaction-safe views |
| `machines/utils.py` | AvailabilityChecker utility class |

## 🔍 Overlap Detection Formula

```python
# Standard overlap formula:
# (start < existing_end) AND (end > existing_start)

overlapping = Rental.objects.filter(
    machine=machine,
    status__in=['approved', 'pending'],
    start_date__lt=end_date,      # ← Key condition 1
    end_date__gt=start_date        # ← Key condition 2
)
```

## ✅ Validation Rules

1. **End date >= Start date** - Database constraint
2. **Start date > Today** - Form validation
3. **Max 30 days** - Form validation
4. **Min 1 day advance** - Form validation
5. **No overlaps** - Model method check
6. **No maintenance** - Maintenance table check

## 🔗 API Endpoints

### Check Availability (AJAX)
```javascript
POST /machines/api/check-availability/

{
  "machine_id": 1,
  "start_date": "2025-12-10",
  "end_date": "2025-12-15"
}

Response:
{
  "available": true,
  "message": "✅ Machine is available",
  "rental_days": 6,
  "blocked_dates": []
}
```

### Get Blocked Dates
```javascript
GET /machines/api/machine/1/blocked-dates/?start_date=2025-12-01&end_date=2025-12-31

Response:
{
  "success": true,
  "blocked_dates": [
    {
      "start": "2025-12-10",
      "end": "2025-12-15",
      "type": "rental",
      "status": "approved"
    }
  ]
}
```

## 🎨 Frontend Integration

### Basic AJAX Check
```javascript
function checkAvailability() {
    const data = {
        machine_id: document.getElementById('id_machine').value,
        start_date: document.getElementById('id_start_date').value,
        end_date: document.getElementById('id_end_date').value
    };
    
    fetch('/machines/api/check-availability/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.available) {
            showSuccess(data.message);
            enableSubmit();
        } else {
            showError(data.message);
            disableSubmit();
        }
    });
}
```

## 🗄️ Database Indexes

```sql
-- Automatically created by Django migrations
CREATE INDEX rental_availability_idx ON machines_rental(machine_id, start_date, end_date, status);
CREATE INDEX rental_dates_idx ON machines_rental(start_date, end_date);
CREATE INDEX rental_user_status_idx ON machines_rental(user_id, status);
```

## 🔧 Management Commands

### Clear Recent Rentals
```bash
# Dry run (see what would be deleted)
python manage.py clear_recent_rentals --dry-run

# Delete last 7 days
python manage.py clear_recent_rentals --days 7

# Delete only pending
python manage.py clear_recent_rentals --status pending
```

### Update Rental Status
```bash
# Run manually
python manage.py update_rental_status

# Dry run
python manage.py update_rental_status --dry-run

# Add to crontab (run every hour)
0 * * * * cd /path/to/project && python manage.py update_rental_status
```

## 🐛 Common Issues & Solutions

### Issue: Double bookings still happening
**Solution**: Ensure you're using `@transaction.atomic` and `select_for_update()`

```python
@transaction.atomic
def create_rental(request):
    machine = Machine.objects.select_for_update().get(pk=machine_id)
    # ... rest of code
```

### Issue: AJAX not working
**Solution**: Check CSRF token is included

```javascript
headers: {
    'X-CSRFToken': getCookie('csrftoken')
}
```

### Issue: Slow queries
**Solution**: Verify indexes are created

```bash
python manage.py sqlmigrate machines 0001  # Check SQL
python manage.py showmigrations  # Verify applied
```

## 📊 Performance Tips

1. **Use select_related()** for foreign keys
```python
rentals = Rental.objects.select_related('machine', 'user').all()
```

2. **Use exists()** instead of count()
```python
# Good
if Rental.objects.filter(...).exists():

# Bad
if Rental.objects.filter(...).count() > 0:
```

3. **Cache availability checks**
```python
from django.core.cache import cache

cache_key = f'avail_{machine_id}_{start}_{end}'
result = cache.get(cache_key)
if not result:
    result = check_availability(...)
    cache.set(cache_key, result, 300)  # 5 min
```

## 🧪 Testing Checklist

- [ ] Create rental with valid dates
- [ ] Try to create overlapping rental (should fail)
- [ ] Update existing rental to overlap (should fail)
- [ ] Check AJAX endpoint returns correct data
- [ ] Verify indexes exist in database
- [ ] Test with concurrent users
- [ ] Check maintenance conflicts
- [ ] Verify past dates are rejected
- [ ] Test 30-day limit
- [ ] Check admin approval workflow

## 📞 Support

For issues or questions:
1. Check logs: `tail -f logs/django.log`
2. Run diagnostics: `python manage.py check`
3. Test database: `python manage.py dbshell`
4. Review this guide: `RENTAL_SYSTEM_COMPLETE_IMPLEMENTATION.md`

---

**Quick Reference v2.0** | Last Updated: Dec 2, 2024
