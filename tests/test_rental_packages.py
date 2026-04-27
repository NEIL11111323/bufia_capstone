from datetime import timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bufia.models import Payment
from machines.models import Machine, Rental, RentalPackage, RentalPackageItem


User = get_user_model()


class RentalPackageFlowTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username='package-member',
            email='package-member@example.com',
            password='secret123',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            username='package-admin',
            email='package-admin@example.com',
            password='secret123',
            is_staff=True,
        )
        self.tractor = Machine.objects.create(
            name='Package Tractor',
            machine_type='tractor_4wd',
            status='available',
            rental_fee_per_day=Decimal('1500.00'),
            current_price='1500/hectare',
            rental_price_type='cash',
            allow_online_payment=False,
            allow_face_to_face_payment=True,
            settlement_type='immediate',
        )
        self.thresher = Machine.objects.create(
            name='Package Thresher',
            machine_type='thresher',
            status='available',
            rental_fee_per_day=Decimal('50.00'),
            current_price='50/sack',
            rental_price_type='cash',
            allow_online_payment=False,
            allow_face_to_face_payment=True,
            settlement_type='immediate',
        )
        self.start_date = timezone.localdate() + timedelta(days=3)

    def test_verified_member_can_create_package_request_with_selected_services(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('machines:rental_package_create'),
            {
                'package_name': 'Rice Season Package',
                'farmer_name': 'Juan Dela Cruz',
                'location': 'Purok 1, Sample Farm',
                'area': '2.5',
                'preferred_start_date': self.start_date.isoformat(),
                'preferred_timeline_notes': 'Start after irrigation release',
                'payment_preference': 'face_to_face',
                'notes': 'Please group the land preparation steps closely.',
                'include_tractor': 'on',
                'include_thresher': 'on',
            },
        )

        package = RentalPackage.objects.get()

        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[package.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(package.user, self.member)
        self.assertEqual(package.farmer_name, 'Juan Dela Cruz')
        self.assertEqual(package.location, 'Purok 1, Sample Farm')
        self.assertEqual(package.total_amount, Decimal('3750.00'))

        tractor_item = package.items.get(service_code='tractor')
        thresher_item = package.items.get(service_code='thresher')

        self.assertEqual(tractor_item.quantity, Decimal('2.5000'))
        self.assertEqual(tractor_item.subtotal, Decimal('3750.00'))
        self.assertEqual(tractor_item.status, 'requested')
        self.assertEqual(thresher_item.pricing_unit, 'sack')
        self.assertEqual(thresher_item.quantity, Decimal('0.0000'))
        self.assertEqual(thresher_item.status, 'tentative')

    def test_admin_approval_creates_linked_rentals_using_item_quantities(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Harvest Support Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.5000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        tractor_item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.5000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )
        thresher_item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.thresher,
            service_code='thresher',
            service_name='Thresher',
            machine_type_required='thresher',
            pricing_unit='sack',
            rate=Decimal('50.00'),
            quantity=Decimal('12.0000'),
            suggested_start=self.start_date + timedelta(days=90),
            suggested_end=self.start_date + timedelta(days=90),
            scheduled_start=self.start_date + timedelta(days=90),
            scheduled_end=self.start_date + timedelta(days=90),
            status='scheduled',
            sequence_order=2,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        formset = response.context['formset']
        prefix = formset.prefix

        approval_payload = {
            f'{prefix}-TOTAL_FORMS': str(formset.total_form_count()),
            f'{prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-id': str(tractor_item.pk),
            f'{prefix}-0-machine': str(self.tractor.pk),
            f'{prefix}-0-quantity': '2.5000',
            f'{prefix}-0-scheduled_start': self.start_date.isoformat(),
            f'{prefix}-0-scheduled_end': self.start_date.isoformat(),
            f'{prefix}-0-status': 'scheduled',
            f'{prefix}-0-notes': '',
            f'{prefix}-1-id': str(thresher_item.pk),
            f'{prefix}-1-machine': str(self.thresher.pk),
            f'{prefix}-1-quantity': '12.0000',
            f'{prefix}-1-scheduled_start': (self.start_date + timedelta(days=90)).isoformat(),
            f'{prefix}-1-scheduled_end': (self.start_date + timedelta(days=90)).isoformat(),
            f'{prefix}-1-status': 'scheduled',
            f'{prefix}-1-notes': '',
            'action': 'approve',
        }

        response = self.client.post(
            reverse('machines:rental_package_detail', args=[package.pk]),
            approval_payload,
            follow=True,
        )

        package.refresh_from_db()
        tractor_item.refresh_from_db()
        thresher_item.refresh_from_db()
        tractor_rental = tractor_item.linked_rental
        thresher_rental = thresher_item.linked_rental

        self.assertEqual(response.status_code, 200)
        self.assertEqual(package.status, 'approved')
        self.assertEqual(package.approved_by, self.admin)
        self.assertIsNotNone(tractor_rental)
        self.assertIsNotNone(thresher_rental)
        self.assertEqual(tractor_rental.area, Decimal('2.5000'))
        self.assertEqual(tractor_rental.payment_amount, Decimal('3750.00'))
        self.assertEqual(thresher_rental.area, Decimal('12.0000'))
        self.assertEqual(thresher_rental.payment_amount, Decimal('600.00'))
        self.assertEqual(thresher_rental.payment_method, 'face_to_face')
        self.assertIn('Service Quantity: 12.0000 sack', thresher_rental.purpose)

        rental_content_type = ContentType.objects.get_for_model(tractor_rental)
        self.assertTrue(
            Payment.objects.filter(
                content_type=rental_content_type,
                object_id=tractor_rental.pk,
                amount=Decimal('3750.00'),
            ).exists()
        )
        self.assertTrue(
            Payment.objects.filter(
                content_type=rental_content_type,
                object_id=thresher_rental.pk,
                amount=Decimal('600.00'),
            ).exists()
        )

    def test_member_equipment_rentals_page_links_to_package_workspace(self):
        RentalPackage.objects.create(
            user=self.member,
            package_name='Member Package View',
            farmer_name='Package Member',
            location='Member Farm',
            area=Decimal('1.5000'),
            preferred_start_date=self.start_date,
            status='pending',
            payment_status='pending',
        )
        self.client.force_login(self.member)

        response = self.client.get(reverse('machines:rental_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('machines:rental_package_list'))
        self.assertContains(response, 'Package Requests')
        self.assertNotContains(response, 'Equipment Rental Package Requests')
        self.assertNotContains(response, 'Member Package View')

    def test_admin_equipment_rentals_page_shows_package_requests_section(self):
        RentalPackage.objects.create(
            user=self.member,
            package_name='Admin Package View',
            farmer_name='Package Member',
            location='Admin Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            status='pending',
            payment_status='pending',
        )
        self.client.force_login(self.admin)

        dashboard_response = self.client.get(reverse('machines:admin_rental_dashboard'))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Equipment Rental Package Requests')
        self.assertContains(dashboard_response, 'Admin Package View')
        self.assertContains(dashboard_response, reverse('machines:rental_package_list'))
        self.assertContains(dashboard_response, 'View All Packages')

    def test_confirm_schedule_creates_package_reserve_and_blocks_machine_dates(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Schedule Confirmation Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        tractor_item = RentalPackageItem.objects.create(
            rental_package=package,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            status='requested',
            sequence_order=1,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        formset = response.context['formset']
        prefix = formset.prefix

        confirm_payload = {
            f'{prefix}-TOTAL_FORMS': str(formset.total_form_count()),
            f'{prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-id': str(tractor_item.pk),
            f'{prefix}-0-machine': str(self.tractor.pk),
            f'{prefix}-0-quantity': '2.0000',
            f'{prefix}-0-scheduled_start': self.start_date.isoformat(),
            f'{prefix}-0-scheduled_end': self.start_date.isoformat(),
            f'{prefix}-0-status': 'requested',
            f'{prefix}-0-notes': '',
            'action': f'confirm_item:{tractor_item.pk}',
        }

        self.client.post(
            reverse('machines:rental_package_detail', args=[package.pk]),
            confirm_payload,
            follow=True,
        )

        tractor_item.refresh_from_db()
        self.assertEqual(tractor_item.status, 'scheduled')
        self.assertIsNotNone(tractor_item.linked_rental_id)

        calendar_response = self.client.get(reverse('machines:machine_calendar_events', args=[self.tractor.pk]))
        calendar_titles = [event['title'] for event in calendar_response.json()]
        self.assertIn('Package Reserve', calendar_titles)

        availability_response = self.client.post(
            reverse('machines:check_date_availability'),
            data=json.dumps({
                'machine_id': self.tractor.pk,
                'start_date': self.start_date.isoformat(),
                'end_date': self.start_date.isoformat(),
            }),
            content_type='application/json',
        )
        availability_payload = availability_response.json()
        self.assertFalse(availability_payload['available'])
        self.assertIn('already booked', availability_payload['message'])

    def test_preapprove_keeps_undecided_items_open_but_reserves_confirmed_ones(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Preapprove Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        tractor_item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )
        thresher_item = RentalPackageItem.objects.create(
            rental_package=package,
            service_code='thresher',
            service_name='Thresher',
            machine_type_required='thresher',
            pricing_unit='sack',
            rate=Decimal('50.00'),
            quantity=Decimal('12.0000'),
            suggested_start=self.start_date + timedelta(days=90),
            suggested_end=self.start_date + timedelta(days=90),
            status='tentative',
            is_tentative=True,
            sequence_order=2,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        formset = response.context['formset']
        prefix = formset.prefix

        payload = {
            f'{prefix}-TOTAL_FORMS': str(formset.total_form_count()),
            f'{prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
            f'{prefix}-0-id': str(tractor_item.pk),
            f'{prefix}-0-machine': str(self.tractor.pk),
            f'{prefix}-0-quantity': '2.0000',
            f'{prefix}-0-scheduled_start': self.start_date.isoformat(),
            f'{prefix}-0-scheduled_end': self.start_date.isoformat(),
            f'{prefix}-0-status': 'scheduled',
            f'{prefix}-0-notes': '',
            f'{prefix}-1-id': str(thresher_item.pk),
            f'{prefix}-1-machine': '',
            f'{prefix}-1-quantity': '12.0000',
            f'{prefix}-1-scheduled_start': '',
            f'{prefix}-1-scheduled_end': '',
            f'{prefix}-1-is_tentative': 'on',
            f'{prefix}-1-status': 'tentative',
            f'{prefix}-1-notes': 'Harvest timing still undecided',
            'action': 'preapprove',
        }

        self.client.post(reverse('machines:rental_package_detail', args=[package.pk]), payload, follow=True)

        package.refresh_from_db()
        tractor_item.refresh_from_db()
        thresher_item.refresh_from_db()
        self.assertEqual(package.status, 'partially_scheduled')
        self.assertEqual(package.approved_by, self.admin)
        self.assertIsNotNone(tractor_item.linked_rental_id)
        self.assertIsNone(thresher_item.linked_rental_id)
        self.assertEqual(thresher_item.status, 'tentative')

    def test_member_can_cancel_own_package_request(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Cancelable Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        item = RentalPackageItem.objects.create(
            rental_package=package,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            status='requested',
            sequence_order=1,
        )

        self.client.force_login(self.member)
        response = self.client.post(
            reverse('machines:rental_package_detail', args=[package.pk]),
            {'action': 'cancel_package'},
            follow=True,
        )

        package.refresh_from_db()
        item.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(package.status, 'cancelled')
        self.assertEqual(item.status, 'cancelled')
        self.assertContains(response, 'Package request cancelled successfully.')

    def test_member_package_detail_groups_cash_and_rice_share_actions(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Mixed Action Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='online',
            status='approved',
            payment_status='partially_paid',
        )
        cash_rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='online',
            payment_amount=Decimal('3000.00'),
            payment_status='pending',
            status='approved',
            workflow_state='approved',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=cash_rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )
        harvester = Machine.objects.create(
            name='Mixed Action Harvester',
            machine_type='harvester',
            status='available',
            current_price='in-kind',
            rental_price_type='in_kind',
            settlement_type='after_harvest',
            in_kind_farmer_share=9,
            in_kind_organization_share=1,
        )
        in_kind_rental = Rental.objects.create(
            machine=harvester,
            user=self.member,
            customer_name='Package Member',
            customer_address='Harvest Area',
            field_location='Harvest Area',
            area=Decimal('10.0000'),
            start_date=self.start_date + timedelta(days=90),
            end_date=self.start_date + timedelta(days=90),
            payment_type='in_kind',
            payment_status='pending',
            settlement_type='after_harvest',
            settlement_status='waiting_for_delivery',
            organization_share_required=Decimal('10.00'),
            organization_share_received=Decimal('0.00'),
            status='approved',
            workflow_state='harvest_report_submitted',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=harvester,
            linked_rental=in_kind_rental,
            service_code='harvester',
            service_name='Harvester',
            machine_type_required='harvester',
            pricing_unit='sack',
            rate=Decimal('0.00'),
            quantity=Decimal('10.0000'),
            suggested_start=self.start_date + timedelta(days=90),
            suggested_end=self.start_date + timedelta(days=90),
            scheduled_start=self.start_date + timedelta(days=90),
            scheduled_end=self.start_date + timedelta(days=90),
            status='scheduled',
            sequence_order=2,
        )

        self.client.force_login(self.member)
        response = self.client.get(
            reverse('machines:rental_package_detail', args=[package.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Package Workflow')
        self.assertContains(response, 'Assign Operators')
        self.assertContains(response, 'BUFIA is preparing the operator assignment for this machine.')
        self.assertNotContains(response, 'Pay Now')
        self.assertContains(response, '10 sacks due')

    def test_package_face_to_face_payment_action_returns_to_package_detail(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Package Cash Flow',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='approved',
            payment_status='pending',
        )
        rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='face_to_face',
            payment_amount=Decimal('3000.00'),
            payment_status='pending',
            status='approved',
            workflow_state='approved',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:record_face_to_face_payment', args=[rental.pk]),
            {
                'payment_amount': '3000.00',
                'next': reverse('machines:rental_package_detail', args=[package.pk]),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[package.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(rental.payment_verified)
        self.assertEqual(rental.workflow_state, 'in_progress')

    def test_package_admin_can_record_cash_payment_when_payment_method_is_blank(self):
        operator = User.objects.create_user(
            username='package-cash-operator',
            email='package-cash-operator@example.com',
            password='secret123',
            role=User.OPERATOR,
        )
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Package Cash Flow Blank Method',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='',
            status='approved',
            payment_status='pending',
        )
        rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='',
            payment_amount=Decimal('3000.00'),
            payment_status='pending',
            payment_verified=False,
            status='approved',
            workflow_state='ready_for_payment',
            assigned_operator=operator,
            operator_status='assigned',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )

        self.client.force_login(self.admin)

        page_response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        self.assertContains(page_response, reverse('machines:record_face_to_face_payment', args=[rental.pk]))

        response = self.client.post(
            reverse('machines:record_face_to_face_payment', args=[rental.pk]),
            {
                'payment_amount': '3000.00',
                'next': reverse('machines:rental_package_detail', args=[package.pk]),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('machines:rental_package_detail', args=[package.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.payment_method, 'face_to_face')
        self.assertTrue(rental.payment_verified)
        self.assertEqual(rental.workflow_state, 'in_progress')

    def test_package_cash_workflow_keeps_operator_assignment_on_package_page(self):
        operator = User.objects.create_user(
            username='package-operator',
            email='package-operator@example.com',
            password='secret123',
            role=User.OPERATOR,
        )
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Operator Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='approved',
            payment_status='partially_paid',
        )
        rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='face_to_face',
            payment_amount=Decimal('3000.00'),
            payment_status='pending',
            payment_verified=False,
            status='approved',
            workflow_state='approved',
            operator_status='unassigned',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )

        self.client.force_login(self.admin)

        package_response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        self.assertEqual(package_response.status_code, 200)
        self.assertContains(package_response, 'Assign Operators')
        self.assertContains(package_response, reverse('machines:assign_operator', args=[rental.pk]))
        self.assertContains(package_response, 'cash rentals can move straight into payment')

        assign_response = self.client.post(
            reverse('machines:assign_operator', args=[rental.pk]),
            {
                'assigned_operator': str(operator.pk),
                'operator_notes': 'Package flow assignment',
                'next': reverse('machines:rental_package_detail', args=[package.pk]),
            },
        )

        rental.refresh_from_db()
        self.assertRedirects(
            assign_response,
            reverse('machines:rental_package_detail', args=[package.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(rental.assigned_operator, operator)
        self.assertEqual(rental.operator_status, 'assigned')
        self.assertEqual(rental.workflow_state, 'ready_for_payment')

        updated_package_response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))
        self.assertContains(updated_package_response, 'Ready for Payment')

        admin_rental_response = self.client.get(reverse('machines:admin_approve_rental', args=[rental.pk]))
        self.assertEqual(admin_rental_response.status_code, 200)
        self.assertContains(admin_rental_response, 'Package-linked rental')
        self.assertNotContains(admin_rental_response, '<h2 class="review-card__title">Operator Assignment</h2>', html=False)

    def test_admin_can_reject_package_and_release_linked_rentals(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Rejectable Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='approved',
            payment_status='pending',
        )
        linked_rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='face_to_face',
            payment_amount=Decimal('3000.00'),
            status='approved',
            workflow_state='approved',
            operator_status='unassigned',
        )
        item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=linked_rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('machines:rental_package_detail', args=[package.pk]),
            {'action': 'reject_package'},
            follow=True,
        )

        package.refresh_from_db()
        item.refresh_from_db()
        linked_rental.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(package.status, 'cancelled')
        self.assertEqual(item.status, 'cancelled')
        self.assertEqual(linked_rental.status, 'cancelled')
        self.assertEqual(linked_rental.workflow_state, 'cancelled')
        self.assertContains(response, 'Package request rejected.')

    def test_day_pricing_uses_scheduled_day_count_for_package_subtotal(self):
        self.tractor.current_price = '2000/day'
        self.tractor.rental_fee_per_day = Decimal('2000.00')
        self.tractor.save(update_fields=['current_price', 'rental_fee_per_day'])

        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Day Rate Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        tractor_item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='day',
            rate=Decimal('2000.00'),
            quantity=Decimal('1.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date + timedelta(days=2),
            scheduled_start=self.start_date,
            scheduled_end=self.start_date + timedelta(days=2),
            status='scheduled',
            sequence_order=1,
        )

        tractor_item.save()
        tractor_item.refresh_from_db()
        self.assertEqual(tractor_item.subtotal, Decimal('6000.00'))

    def test_package_detail_shows_identifiable_quantity_labels(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Label Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('3.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='pending',
            payment_status='pending',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('4000.00'),
            quantity=Decimal('3.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('machines:rental_package_detail', args=[package.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Billable Qty')
        self.assertContains(response, 'Hectares')
        self.assertContains(response, 'Auto from package area')
        self.assertContains(response, 'Workflow Status')
        self.assertContains(response, 'Admin Notes')
        self.assertContains(response, 'Open Availability')
        self.assertContains(response, 'Availability Calendar')

    def test_mixed_package_payment_status_stays_partial_until_in_kind_settlement_is_completed(self):
        package = RentalPackage.objects.create(
            user=self.member,
            package_name='Mixed Payment Package',
            farmer_name='Package Member',
            location='Package Farm',
            area=Decimal('2.0000'),
            preferred_start_date=self.start_date,
            payment_preference='face_to_face',
            status='approved',
            payment_status='pending',
        )
        tractor_rental = Rental.objects.create(
            machine=self.tractor,
            user=self.member,
            customer_name='Package Member',
            customer_address='Package Farm',
            field_location='Package Farm',
            area=Decimal('2.0000'),
            start_date=self.start_date,
            end_date=self.start_date,
            payment_type='cash',
            payment_method='face_to_face',
            payment_amount=Decimal('3000.00'),
            payment_status='paid',
            payment_verified=True,
            status='approved',
            workflow_state='approved',
        )
        tractor_item = RentalPackageItem.objects.create(
            rental_package=package,
            machine=self.tractor,
            linked_rental=tractor_rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor_4wd',
            pricing_unit='hectare',
            rate=Decimal('1500.00'),
            quantity=Decimal('2.0000'),
            suggested_start=self.start_date,
            suggested_end=self.start_date,
            scheduled_start=self.start_date,
            scheduled_end=self.start_date,
            status='scheduled',
            sequence_order=1,
        )
        harvester = Machine.objects.create(
            name='Package Harvester',
            machine_type='harvester',
            status='available',
            current_price='in-kind',
            rental_price_type='in_kind',
            settlement_type='after_harvest',
            in_kind_farmer_share=9,
            in_kind_organization_share=1,
        )
        harvester_rental = Rental.objects.create(
            machine=harvester,
            user=self.member,
            customer_name='Package Member',
            customer_address='Harvest Area',
            field_location='Harvest Area',
            area=Decimal('12.0000'),
            start_date=self.start_date + timedelta(days=90),
            end_date=self.start_date + timedelta(days=90),
            payment_type='in_kind',
            payment_status='pending',
            settlement_type='after_harvest',
            settlement_status='waiting_for_delivery',
            total_harvest_sacks=Decimal('108.00'),
            organization_share_required=Decimal('12.00'),
            organization_share_received=Decimal('0.00'),
            status='approved',
            workflow_state='harvest_report_submitted',
        )
        RentalPackageItem.objects.create(
            rental_package=package,
            machine=harvester,
            linked_rental=harvester_rental,
            service_code='harvester',
            service_name='Harvester',
            machine_type_required='harvester',
            pricing_unit='sack',
            rate=Decimal('0.00'),
            quantity=Decimal('12.0000'),
            suggested_start=self.start_date + timedelta(days=90),
            suggested_end=self.start_date + timedelta(days=90),
            scheduled_start=self.start_date + timedelta(days=90),
            scheduled_end=self.start_date + timedelta(days=90),
            status='scheduled',
            sequence_order=2,
        )

        package.refresh_payment_status(save=True)
        package.refresh_from_db()
        self.assertEqual(tractor_item.linked_rental.payment_status, 'paid')
        self.assertEqual(package.payment_status, 'partially_paid')

        harvester_rental.organization_share_received = Decimal('12.00')
        harvester_rental.payment_status = 'paid_in_kind'
        harvester_rental.settlement_status = 'paid'
        harvester_rental.status = 'completed'
        harvester_rental.workflow_state = 'completed'
        harvester_rental.payment_verified = True
        harvester_rental.save(update_fields=[
            'organization_share_received',
            'payment_status',
            'settlement_status',
            'status',
            'workflow_state',
            'payment_verified',
            'updated_at',
        ])

        package.refresh_payment_status(save=True)
        package.refresh_from_db()
        self.assertEqual(package.payment_status, 'paid')
