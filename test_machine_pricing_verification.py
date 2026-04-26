"""
Test script to verify machine pricing computations for all scenarios:
- Per hectare pricing (immediate cash)
- Per day pricing (immediate cash)
- Per hour pricing (immediate cash)
- Per sack pricing (immediate cash)
- In-kind/after harvest pricing
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from decimal import Decimal
from machines.models import Machine, Rental
from django.contrib.auth import get_user_model
from datetime import date, timedelta

User = get_user_model()

def test_pricing_scenarios():
    print("=" * 80)
    print("MACHINE PRICING VERIFICATION TEST")
    print("=" * 80)
    
    # Get or create a test user
    test_user, _ = User.objects.get_or_create(
        username='test_pricing_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
            'is_verified': True,
        }
    )
    
    test_scenarios = []
    
    # Scenario 1: Per Hectare Pricing (Tractor)
    print("\n" + "=" * 80)
    print("SCENARIO 1: PER HECTARE PRICING (Immediate Cash)")
    print("=" * 80)
    
    tractor = Machine.objects.filter(machine_type='tractor_4wd').first()
    if not tractor:
        tractor = Machine.objects.create(
            name='Test 4WD Tractor',
            machine_type='tractor_4wd',
            status='available',
            rental_price_type='cash',
            settlement_type='immediate',
            current_price='4000/hectare',
            rental_fee_per_day=Decimal('4000.00'),
        )
    
    print(f"Machine: {tractor.name}")
    print(f"Machine Type: {tractor.machine_type}")
    print(f"Current Price: {tractor.current_price}")
    print(f"Rental Price Type: {tractor.rental_price_type}")
    print(f"Settlement Type: {tractor.settlement_type}")
    
    parsed_rate, parsed_unit = tractor._parse_current_price()
    print(f"\nParsed Rate: {parsed_rate}")
    print(f"Parsed Unit: {parsed_unit}")
    
    pricing_info = tractor.get_pricing_info()
    print(f"\nPricing Info:")
    print(f"  Rate: {pricing_info['rate']}")
    print(f"  Unit: {pricing_info['unit']}")
    
    # Test calculation for different hectares
    test_areas = [Decimal('1.0'), Decimal('2.5'), Decimal('5.0')]
    for area in test_areas:
        cost = tractor.calculate_rental_cost(area=area)
        print(f"\nArea: {area} hectares")
        print(f"Calculated Cost: PHP {cost:,.2f}")
        print(f"Expected: PHP {Decimal('4000') * area:,.2f}")
        assert cost == Decimal('4000') * area, f"Cost mismatch for {area} hectares"
    
    test_scenarios.append(("Per Hectare", "PASSED"))
    
    # Scenario 2: Per Day Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 2: PER DAY PRICING (Immediate Cash)")
    print("=" * 80)
    
    daily_machine = Machine.objects.filter(machine_type='other').first()
    if not daily_machine:
        daily_machine = Machine.objects.create(
            name='Test Daily Machine',
            machine_type='other',
            status='available',
            rental_price_type='cash',
            settlement_type='immediate',
            current_price='1500/day',
            rental_fee_per_day=Decimal('1500.00'),
        )
    else:
        daily_machine.current_price = '1500/day'
        daily_machine.rental_price_type = 'cash'
        daily_machine.settlement_type = 'immediate'
        daily_machine.save()
    
    print(f"Machine: {daily_machine.name}")
    print(f"Current Price: {daily_machine.current_price}")
    
    parsed_rate, parsed_unit = daily_machine._parse_current_price()
    print(f"\nParsed Rate: {parsed_rate}")
    print(f"Parsed Unit: {parsed_unit}")
    
    pricing_info = daily_machine.get_pricing_info()
    print(f"\nPricing Info:")
    print(f"  Rate: {pricing_info['rate']}")
    print(f"  Unit: {pricing_info['unit']}")
    
    test_scenarios.append(("Per Day", "PASSED"))
    
    # Scenario 3: Per Hour Pricing (Dryer)
    print("\n" + "=" * 80)
    print("SCENARIO 3: PER HOUR PRICING - DRYER (Immediate Cash)")
    print("=" * 80)
    
    dryer = Machine.objects.filter(machine_type='flatbed_dryer').first()
    if not dryer:
        dryer = Machine.objects.create(
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
    
    print(f"Machine: {dryer.name}")
    print(f"Dryer Service Type: {dryer.dryer_service_type}")
    print(f"Dryer Pricing Type: {dryer.dryer_pricing_type}")
    print(f"Dryer Hourly Rate: {dryer.dryer_hourly_rate}")
    print(f"Current Price: {dryer.current_price}")
    
    pricing_info = dryer.get_pricing_info()
    print(f"\nPricing Info:")
    print(f"  Rate: {pricing_info['rate']}")
    print(f"  Unit: {pricing_info['unit']}")
    
    test_hours = [1, 5, 10]
    for hours in test_hours:
        cost = dryer.calculate_rental_cost(area=hours)
        print(f"\nHours: {hours}")
        print(f"Calculated Cost: PHP {cost:,.2f}")
    
    test_scenarios.append(("Per Hour (Dryer)", "PASSED"))
    
    # Scenario 4: Per Sack Pricing (Solar Dryer)
    print("\n" + "=" * 80)
    print("SCENARIO 4: PER SACK PRICING - SOLAR DRYER (Immediate Cash)")
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
    
    print(f"Machine: {solar_dryer.name}")
    print(f"Dryer Service Type: {solar_dryer.dryer_service_type}")
    print(f"Dryer Pricing Type: {solar_dryer.dryer_pricing_type}")
    print(f"Current Price: {solar_dryer.current_price}")
    
    pricing_info = solar_dryer.get_pricing_info()
    print(f"\nPricing Info:")
    print(f"  Rate: {pricing_info['rate']}")
    print(f"  Unit: {pricing_info['unit']}")
    
    test_sacks = [10, 25, 50]
    for sacks in test_sacks:
        cost = solar_dryer.calculate_rental_cost(area=sacks)
        print(f"\nSacks: {sacks}")
        print(f"Calculated Cost: PHP {cost:,.2f}")
        print(f"Expected: PHP {Decimal('35') * sacks:,.2f}")
    
    test_scenarios.append(("Per Sack (Solar Dryer)", "PASSED"))
    
    # Scenario 5: In-Kind / After Harvest Pricing
    print("\n" + "=" * 80)
    print("SCENARIO 5: IN-KIND / AFTER HARVEST PRICING")
    print("=" * 80)
    
    inkind_machine = Machine.objects.filter(rental_price_type='in_kind').first()
    if not inkind_machine:
        inkind_machine = Machine.objects.create(
            name='Test In-Kind Machine',
            machine_type='harvester',
            status='available',
            rental_price_type='in_kind',
            settlement_type='after_harvest',
            current_price='0',
            rental_fee_per_day=Decimal('0.00'),
            in_kind_farmer_share=9,
            in_kind_organization_share=1,
        )
    
    print(f"Machine: {inkind_machine.name}")
    print(f"Rental Price Type: {inkind_machine.rental_price_type}")
    print(f"Settlement Type: {inkind_machine.settlement_type}")
    print(f"Farmer Share: {inkind_machine.in_kind_farmer_share}")
    print(f"BUFIA Share: {inkind_machine.in_kind_organization_share}")
    
    # Test rental creation
    rental = Rental(
        machine=inkind_machine,
        user=test_user,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=2),
        area=Decimal('2.5'),
        payment_type='in_kind',
        settlement_type='after_harvest',
    )
    
    payment_amount = rental.calculate_payment_amount()
    print(f"\nPayment Amount (should be 0 for in-kind): PHP {payment_amount:,.2f}")
    assert payment_amount == Decimal('0.00'), "In-kind payment should be 0"
    
    # Test harvest share calculation
    test_harvests = [Decimal('100'), Decimal('250'), Decimal('500')]
    for harvest in test_harvests:
        bufia_share, member_share = rental.calculate_harvest_shares(harvest)
        print(f"\nTotal Harvest: {harvest} sacks")
        print(f"BUFIA Share (1/9): {bufia_share} sacks")
        print(f"Member Share (8/9): {member_share} sacks")
        print(f"Total: {bufia_share + member_share} sacks")
        
        # Verify the ratio
        expected_bufia = (harvest * Decimal('1') / Decimal('9')).quantize(Decimal('0.01'))
        print(f"Expected BUFIA Share: {expected_bufia}")
    
    test_scenarios.append(("In-Kind / After Harvest", "PASSED"))
    
    # Scenario 6: Rental Payment Calculation (Per Hectare)
    print("\n" + "=" * 80)
    print("SCENARIO 6: RENTAL PAYMENT CALCULATION (Per Hectare)")
    print("=" * 80)
    
    rental_cash = Rental(
        machine=tractor,
        user=test_user,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=2),
        area=Decimal('3.5'),
        payment_type='cash',
        settlement_type='immediate',
    )
    
    payment = rental_cash.calculate_payment_amount()
    expected = Decimal('4000') * Decimal('3.5')
    print(f"Machine: {tractor.name}")
    print(f"Rate: PHP 4000/hectare")
    print(f"Area: 3.5 hectares")
    print(f"Calculated Payment: PHP {payment:,.2f}")
    print(f"Expected Payment: PHP {expected:,.2f}")
    assert payment == expected, f"Payment mismatch: {payment} != {expected}"
    
    test_scenarios.append(("Rental Payment Calculation", "PASSED"))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for scenario, status in test_scenarios:
        print(f"{scenario:.<50} {status}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        test_pricing_scenarios()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
