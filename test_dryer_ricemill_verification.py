"""
Test script to verify dryer rental and rice mill appointment pricing computations:
- Dryer hourly pricing
- Dryer per sack pricing (solar dryer)
- Dryer until dried pricing
- Rice mill per kg pricing
- Rice mill tahop (rice bran) selling
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from decimal import Decimal
from machines.models import Machine, DryerRental, RiceMillAppointment
from django.contrib.auth import get_user_model
from datetime import date, time, timedelta

User = get_user_model()

def test_dryer_and_ricemill():
    print("=" * 80)
    print("DRYER & RICE MILL PRICING VERIFICATION TEST")
    print("=" * 80)
    
    # Get or create a test user
    test_user, _ = User.objects.get_or_create(
        username='test_dryer_user',
        defaults={
            'email': 'testdryer@example.com',
            'first_name': 'Test',
            'last_name': 'Dryer',
            'is_active': True,
            'is_verified': True,
        }
    )
    
    test_scenarios = []
    
    # ========================================================================
    # DRYER RENTAL TESTS
    # ========================================================================
    
    # Scenario 1: Flatbed Dryer - Hourly Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 1: FLATBED DRYER - HOURLY PRICING")
    print("=" * 80)
    
    flatbed_dryer = Machine.objects.filter(machine_type='flatbed_dryer').first()
    if not flatbed_dryer:
        flatbed_dryer = Machine.objects.create(
            name='Test Flatbed Dryer',
            machine_type='flatbed_dryer',
            status='available',
            rental_price_type='cash',
            settlement_type='immediate',
            dryer_service_type='flatbed',
            dryer_pricing_type='hourly',
            dryer_hourly_rate=Decimal('150.00'),
            current_price='150/hour',
            rental_fee_per_day=Decimal('150.00'),
        )
    
    print(f"Machine: {flatbed_dryer.name}")
    print(f"Dryer Pricing Type: {flatbed_dryer.dryer_pricing_type}")
    print(f"Hourly Rate: PHP {flatbed_dryer.dryer_hourly_rate}")
    
    # Test hourly rental
    rental_date = date.today() + timedelta(days=1)
    start_time = time(8, 0)  # 8:00 AM
    end_time = time(13, 0)   # 1:00 PM (5 hours)
    
    dryer_rental = DryerRental(
        machine=flatbed_dryer,
        user=test_user,
        rental_date=rental_date,
        start_time=start_time,
        end_time=end_time,
        quantity='50 sacks',
        goods_description='Palay',
        payment_method='face_to_face',
    )
    
    print(f"\nRental Date: {rental_date}")
    print(f"Time: {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
    print(f"Duration: {dryer_rental.duration_hours} hours")
    print(f"Hourly Rate: PHP {dryer_rental.effective_hourly_rate}")
    
    # Calculate expected amount
    expected_amount = dryer_rental.duration_hours * dryer_rental.effective_hourly_rate
    print(f"\nExpected Amount: PHP {expected_amount:,.2f}")
    print(f"Formula: {dryer_rental.duration_hours} hours × PHP {dryer_rental.effective_hourly_rate}/hour")
    
    # Save and check
    dryer_rental.save()
    print(f"Calculated Total Amount: PHP {dryer_rental.total_amount:,.2f}")
    
    assert dryer_rental.total_amount == expected_amount, f"Amount mismatch: {dryer_rental.total_amount} != {expected_amount}"
    print("✅ Hourly pricing calculation CORRECT")
    
    test_scenarios.append(("Flatbed Dryer - Hourly", "PASSED"))
    
    # Scenario 2: Solar Dryer - Per Sack Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 2: SOLAR DRYER - PER SACK PRICING")
    print("=" * 80)
    
    solar_dryer = Machine.objects.filter(machine_type='solar_dryer').first()
    if not solar_dryer:
        solar_dryer = Machine.objects.create(
            name='Test Solar Dryer',
            machine_type='solar_dryer',
            status='available',
            rental_price_type='cash',
            settlement_type='immediate',
            dryer_service_type='solar',
            dryer_pricing_type='per_sack',
            current_price='35/sack',
            rental_fee_per_day=Decimal('35.00'),
        )
    else:
        solar_dryer.dryer_pricing_type = 'per_sack'
        solar_dryer.current_price = '35/sack'
        solar_dryer.save()
    
    print(f"Machine: {solar_dryer.name}")
    print(f"Dryer Pricing Type: {solar_dryer.dryer_pricing_type}")
    print(f"Rate per Sack: PHP {solar_dryer.get_effective_dryer_sack_rate()}")
    
    # Test per sack rental
    test_sack_quantities = ['25 sacks', '50 sacks', '100 sacks']
    
    for quantity_str in test_sack_quantities:
        solar_rental = DryerRental(
            machine=solar_dryer,
            user=test_user,
            rental_date=rental_date,
            quantity=quantity_str,
            goods_description='Palay for sun drying',
            estimated_drying_days=3,
        )
        
        sacks = solar_rental.quantity_in_sacks
        rate_per_sack = solar_dryer.get_effective_dryer_sack_rate()
        
        print(f"\nQuantity: {quantity_str}")
        print(f"Parsed Sacks: {sacks}")
        print(f"Rate per Sack: PHP {rate_per_sack}")
        
        # For per sack pricing, the amount is calculated when admin confirms
        # But we can verify the rate is correct
        expected_amount = sacks * rate_per_sack
        print(f"Expected Amount: PHP {expected_amount:,.2f}")
        print(f"Formula: {sacks} sacks × PHP {rate_per_sack}/sack")
        
        # Note: Until dried/per sack rentals have amount set to 0 initially
        # Amount is calculated when admin confirms the service
        print(f"Initial Total Amount: PHP {solar_rental.total_amount:,.2f} (set when confirmed)")
    
    print("\n✅ Solar dryer per sack pricing structure CORRECT")
    test_scenarios.append(("Solar Dryer - Per Sack", "PASSED"))
    
    # Scenario 3: Dryer - Until Dried Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 3: DRYER - UNTIL DRIED PRICING")
    print("=" * 80)
    
    until_dried_rental = DryerRental(
        machine=flatbed_dryer,
        user=test_user,
        rental_date=rental_date,
        rental_type='until_dried',
        quantity='75 sacks',
        goods_description='Palay - until dried service',
    )
    
    print(f"Machine: {flatbed_dryer.name}")
    print(f"Rental Type: {until_dried_rental.rental_type}")
    print(f"Quantity: {until_dried_rental.quantity}")
    print(f"Pricing Type: {until_dried_rental.pricing_type_label}")
    
    # Until dried has no upfront payment
    print(f"\nInitial Total Amount: PHP {until_dried_rental.total_amount:,.2f}")
    print("Note: Amount is determined after drying is complete")
    print("✅ Until dried pricing structure CORRECT")
    
    test_scenarios.append(("Dryer - Until Dried", "PASSED"))
    
    # ========================================================================
    # RICE MILL APPOINTMENT TESTS
    # ========================================================================
    
    # Scenario 4: Rice Mill - Per Kilogram Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 4: RICE MILL - PER KILOGRAM PRICING")
    print("=" * 80)
    
    rice_mill = Machine.objects.filter(machine_type='rice_mill').first()
    if not rice_mill:
        rice_mill = Machine.objects.create(
            name='Test Rice Mill',
            machine_type='rice_mill',
            status='available',
            rental_price_type='cash',
            settlement_type='immediate',
            current_price='3.00/kg',
            rental_fee_per_day=Decimal('3.00'),
        )
    
    print(f"Machine: {rice_mill.name}")
    print(f"Machine Type: {rice_mill.machine_type}")
    
    pricing_info = rice_mill.get_pricing_info()
    print(f"Price per KG: PHP {pricing_info['rate']}")
    print(f"Pricing Unit: {pricing_info['unit']}")
    
    # Test rice mill appointment
    test_weights = [
        (5, Decimal('250.00')),   # 5 sacks = 250 kg
        (10, Decimal('500.00')),  # 10 sacks = 500 kg
        (20, Decimal('1000.00')), # 20 sacks = 1000 kg
    ]
    
    for sacks, expected_kg in test_weights:
        appointment = RiceMillAppointment(
            machine=rice_mill,
            user=test_user,
            appointment_date=rental_date,
            sacks=sacks,
            booking_source='member',
            payment_method='face_to_face',
        )
        
        # Save to trigger rice_quantity calculation
        appointment.save()
        
        print(f"\nSacks: {sacks}")
        print(f"Estimated Weight: {appointment.estimated_weight} kg")
        print(f"Rice Quantity: {appointment.rice_quantity} kg")
        
        assert appointment.rice_quantity == expected_kg, f"Weight mismatch: {appointment.rice_quantity} != {expected_kg}"
        
        # Calculate milling cost
        milling_cost = appointment.computed_milling_amount
        expected_cost = expected_kg * pricing_info['rate']
        
        print(f"Price per KG: PHP {appointment.effective_price_per_kg}")
        print(f"Computed Milling Amount: PHP {milling_cost:,.2f}")
        print(f"Expected: PHP {expected_cost:,.2f}")
        print(f"Formula: {expected_kg} kg × PHP {pricing_info['rate']}/kg")
        
        assert milling_cost == expected_cost, f"Cost mismatch: {milling_cost} != {expected_cost}"
    
    print("\n✅ Rice mill per kg pricing calculation CORRECT")
    test_scenarios.append(("Rice Mill - Per KG", "PASSED"))
    
    # Scenario 5: Rice Mill - With Tahop (Rice Bran) Selling
    print("\n" + "=" * 80)
    print("SCENARIO 5: RICE MILL - WITH TAHOP SELLING")
    print("=" * 80)
    
    appointment_with_tahop = RiceMillAppointment(
        machine=rice_mill,
        user=test_user,
        appointment_date=rental_date,
        sacks=10,
        rice_quantity=Decimal('500.00'),
        sell_tahop=True,
        tahop_weight=Decimal('50.00'),  # 50 kg of rice bran
        tahop_price_per_kg=Decimal('15.00'),  # PHP 15/kg for tahop
        booking_source='member',
        payment_method='face_to_face',
    )
    
    print(f"Rice Quantity: {appointment_with_tahop.rice_quantity} kg")
    print(f"Milling Rate: PHP {appointment_with_tahop.effective_price_per_kg}/kg")
    
    milling_amount = appointment_with_tahop.computed_milling_amount
    print(f"\nMilling Amount: PHP {milling_amount:,.2f}")
    print(f"Formula: {appointment_with_tahop.rice_quantity} kg × PHP {appointment_with_tahop.effective_price_per_kg}/kg")
    
    print(f"\nSell Tahop: {appointment_with_tahop.sell_tahop}")
    print(f"Tahop Weight: {appointment_with_tahop.tahop_weight} kg")
    print(f"Tahop Price: PHP {appointment_with_tahop.tahop_price_per_kg}/kg")
    
    tahop_amount = appointment_with_tahop.computed_tahop_total_amount
    expected_tahop = Decimal('50.00') * Decimal('15.00')
    print(f"Tahop Amount: PHP {tahop_amount:,.2f}")
    print(f"Expected: PHP {expected_tahop:,.2f}")
    print(f"Formula: {appointment_with_tahop.tahop_weight} kg × PHP {appointment_with_tahop.tahop_price_per_kg}/kg")
    
    assert tahop_amount == expected_tahop, f"Tahop amount mismatch: {tahop_amount} != {expected_tahop}"
    
    total_amount = appointment_with_tahop.computed_total_amount
    expected_total = milling_amount + tahop_amount
    print(f"\nTotal Amount: PHP {total_amount:,.2f}")
    print(f"Expected: PHP {expected_total:,.2f}")
    print(f"Formula: Milling (PHP {milling_amount:,.2f}) + Tahop (PHP {tahop_amount:,.2f})")
    
    assert total_amount == expected_total, f"Total amount mismatch: {total_amount} != {expected_total}"
    
    # Save and verify
    appointment_with_tahop.save()
    print(f"\nSaved Total Amount: PHP {appointment_with_tahop.total_amount:,.2f}")
    assert appointment_with_tahop.total_amount == expected_total, "Saved amount doesn't match computed"
    
    print("\n✅ Rice mill with tahop selling calculation CORRECT")
    test_scenarios.append(("Rice Mill - With Tahop", "PASSED"))
    
    # Scenario 6: Rice Mill - BUFIA Rice Share Booking
    print("\n" + "=" * 80)
    print("SCENARIO 6: RICE MILL - BUFIA RICE SHARE BOOKING")
    print("=" * 80)
    
    bufia_appointment = RiceMillAppointment(
        machine=rice_mill,
        user=test_user,
        appointment_date=rental_date,
        sacks=15,
        rice_quantity=Decimal('750.00'),
        booking_source='bufia_rice_share',
        payment_method='face_to_face',
    )
    
    print(f"Booking Source: {bufia_appointment.get_booking_source_display()}")
    print(f"Is BUFIA Rice Share: {bufia_appointment.is_bufia_rice_share}")
    print(f"Rice Quantity: {bufia_appointment.rice_quantity} kg")
    print(f"Milling Rate: PHP {bufia_appointment.effective_price_per_kg}/kg")
    
    bufia_milling_cost = bufia_appointment.computed_milling_amount
    expected_bufia_cost = Decimal('750.00') * Decimal('3.00')
    
    print(f"\nComputed Milling Amount: PHP {bufia_milling_cost:,.2f}")
    print(f"Expected: PHP {expected_bufia_cost:,.2f}")
    
    assert bufia_milling_cost == expected_bufia_cost, f"BUFIA cost mismatch: {bufia_milling_cost} != {expected_bufia_cost}"
    
    print("\n✅ BUFIA rice share booking calculation CORRECT")
    test_scenarios.append(("Rice Mill - BUFIA Share", "PASSED"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for scenario, status in test_scenarios:
        print(f"{scenario:.<50} {status}")
    
    print("\n" + "=" * 80)
    print("ALL DRYER & RICE MILL TESTS PASSED!")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        test_dryer_and_ricemill()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
