#!/usr/bin/env python
"""
Create a clean overdue-rental conflict scenario for the admin dashboard.

This script creates:
1. An approved rental that is already overdue.
2. A second approved rental on the same machine.
3. A forced same-day overlap so the second rental moves into
   workflow_state='conflict_review' after sync.

The overlap is intentionally introduced with QuerySet.update() so we can
simulate stale approved data that would normally be blocked by model
validation.
"""

from datetime import timedelta
from decimal import Decimal
import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bufia.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from machines.models import Machine, Rental


User = get_user_model()


def ensure_demo_user(username):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": f"{username}@example.com",
        },
    )
    if created:
        user.set_password("demo12345")
        user.save(update_fields=["password"])
    return user


def create_demo_machine(label):
    return Machine.objects.create(
        name=f"Demo Overdue Conflict Tractor {label}",
        machine_type="tractor_4wd",
        description="Dedicated demo machine for overdue conflict review testing.",
        status="available",
        rental_fee_per_day=Decimal("1500.00"),
        current_price="1500/day",
    )


def find_safe_booking_day(machine, today):
    for offset in range(1, 31):
        target_day = today + timedelta(days=offset)
        is_available, _ = Rental.check_availability(
            machine=machine,
            start_date=target_day,
            end_date=target_day,
        )
        if is_available:
            return target_day
    raise RuntimeError("Could not find an available future day for the demo conflict rental.")


def create_conflict_scenario():
    today = timezone.localdate()
    label = timezone.now().strftime("%Y%m%d%H%M%S")

    overdue_user = ensure_demo_user(f"demo_overdue_member_a_{label}")
    conflict_user = ensure_demo_user(f"demo_overdue_member_b_{label}")
    machine = create_demo_machine(label)

    overdue_start = today - timedelta(days=5)
    overdue_end = today - timedelta(days=1)

    overdue_rental = Rental.objects.create(
        machine=machine,
        user=overdue_user,
        customer_name=overdue_user.username,
        customer_contact_number="09123456789",
        start_date=overdue_start,
        end_date=overdue_end,
        status="approved",
        workflow_state="approved",
        payment_type="cash",
        payment_status="paid",
        payment_amount=Decimal("500.00"),
        payment_verified=True,
        purpose="Demo overdue rental for conflict scenario",
    )

    safe_day = find_safe_booking_day(machine, today)
    conflict_rental = Rental.objects.create(
        machine=machine,
        user=conflict_user,
        customer_name=conflict_user.username,
        customer_contact_number="09987654321",
        start_date=safe_day,
        end_date=safe_day,
        status="approved",
        workflow_state="approved",
        payment_type="cash",
        payment_status="paid",
        payment_amount=Decimal("750.00"),
        payment_verified=True,
        purpose="Demo approved rental that will be forced into conflict review",
    )

    # Bypass clean() on purpose to simulate stale approved data that now
    # conflicts with an overdue rental still blocking the machine today.
    Rental.objects.filter(pk=conflict_rental.pk).update(
        start_date=today,
        end_date=today,
    )

    Rental.sync_overdue_workflow_states(today=today)
    overdue_rental.refresh_from_db()
    conflict_rental.refresh_from_db()

    print("Created overdue conflict scenario.")
    print(f"Machine: {machine.name} (id={machine.id})")
    print(
        "Overdue rental: "
        f"id={overdue_rental.id}, user={overdue_user.username}, "
        f"dates={overdue_rental.start_date} to {overdue_rental.end_date}, "
        f"workflow={overdue_rental.workflow_state}"
    )
    print(
        "Conflict rental: "
        f"id={conflict_rental.id}, user={conflict_user.username}, "
        f"dates={conflict_rental.start_date} to {conflict_rental.end_date}, "
        f"workflow={conflict_rental.workflow_state}"
    )

    return overdue_rental, conflict_rental


if __name__ == "__main__":
    create_conflict_scenario()
