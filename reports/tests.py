from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from bufia.models import Payment, Refund
from machines.models import Machine, Maintenance, MaintenancePartUsed, Rental, RiceMillAppointment, RentalPackage, RentalPackageItem
from reports.models import RiceSale, RiceSaleSetting
from users.models import MembershipApplication


User = get_user_model()


class ReportsAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='reports-admin',
            email='reports-admin@example.com',
            password='testpass123',
        )
        self.member = User.objects.create_user(
            username='report-member',
            email='member@example.com',
            password='testpass123',
            first_name='Recent',
            last_name='Member',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.application = MembershipApplication.objects.create(
            user=self.member,
            is_approved=True,
            payment_status='pending',
        )
        self.application.land_proof_document = SimpleUploadedFile(
            'membership-proof.jpg',
            b'fake-image-bytes',
            content_type='image/jpeg',
        )
        self.application.land_proof_notes = 'Tax declaration copy attached for verification.'
        self.application.valid_id_document = SimpleUploadedFile(
            'national-id.jpg',
            b'fake-national-id-bytes',
            content_type='image/jpeg',
        )
        self.application.save(update_fields=['land_proof_document', 'land_proof_notes', 'valid_id_document'])
        self.member_without_proof = User.objects.create_user(
            username='report-member-no-proof',
            email='member-no-proof@example.com',
            password='testpass123',
            first_name='Pending',
            last_name='Proof',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.application_without_proof = MembershipApplication.objects.create(
            user=self.member_without_proof,
            is_approved=True,
            payment_status='pending',
        )
        self.member_with_missing_proof = User.objects.create_user(
            username='report-member-missing-proof',
            email='member-missing-proof@example.com',
            password='testpass123',
            first_name='Missing',
            last_name='File',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.application_with_missing_proof = MembershipApplication.objects.create(
            user=self.member_with_missing_proof,
            is_approved=True,
            payment_status='pending',
            land_proof_notes='Stored file path exists in the database but the actual media file is missing.',
        )
        self.application_with_missing_proof.land_proof_document.name = 'membership/land_proofs/rental-receipt-68.pdf'
        self.application_with_missing_proof.save(update_fields=['land_proof_document', 'land_proof_notes'])
        today = timezone.localdate()
        self.recent_machine = Machine.objects.create(
            name='Recent Tractor',
            machine_type='tractor_4wd',
            description='Recent machine',
            current_price='1500',
            brand_name='Kubota',
            model_name='L4508',
            model_year=2024,
            acquisition_date=today - timedelta(days=40),
            acquisition_amount=Decimal('1000.00'),
        )
        self.old_machine = Machine.objects.create(
            name='Old Tractor',
            machine_type='tractor_4wd',
            description='Old machine',
            current_price='1600',
            brand_name='Yanmar',
            model_name='YT235',
            model_year=2023,
            acquisition_date=today - timedelta(days=400),
            acquisition_amount=Decimal('800.00'),
        )
        self.rice_mill_machine = Machine.objects.create(
            name='Harvest Rice Mill',
            machine_type='rice_mill',
            description='Rice mill for harvest report tests',
            current_price='5',
        )
        self.recent_rental = Rental.objects.create(
            machine=self.recent_machine,
            user=self.member,
            start_date=today - timedelta(days=1),
            end_date=today,
            status='completed',
            payment_amount=Decimal('1500.00'),
            payment_status='paid',
            payment_verified=True,
        )
        Rental.objects.create(
            machine=self.old_machine,
            user=self.member,
            start_date=today - timedelta(days=20),
            end_date=today - timedelta(days=19),
            status='completed',
            payment_amount=Decimal('1600.00'),
            payment_status='paid',
            payment_verified=True,
        )
        self.package_rental = Rental.objects.create(
            machine=self.recent_machine,
            user=self.member,
            start_date=today,
            end_date=today + timedelta(days=1),
            status='approved',
            payment_amount=Decimal('800.00'),
            payment_status='pending',
            payment_verified=False,
        )
        self.rental_package = RentalPackage.objects.create(
            user=self.member,
            package_name='Whole Farming Service Package',
            farmer_name=self.member.get_full_name() or self.member.username,
            location='Sector Demo Farm',
            area=Decimal('1.5000'),
            preferred_start_date=today,
            status='approved',
            payment_status='pending',
        )
        RentalPackageItem.objects.create(
            rental_package=self.rental_package,
            machine=self.recent_machine,
            linked_rental=self.package_rental,
            service_code='tractor',
            service_name='Tractor / Plowing',
            machine_type_required='tractor',
            pricing_unit='day',
            rate=Decimal('800.00'),
            quantity=Decimal('1.0000'),
            suggested_start=today,
            suggested_end=today + timedelta(days=1),
            scheduled_start=today,
            scheduled_end=today + timedelta(days=1),
            is_tentative=False,
            status='scheduled',
            subtotal=Decimal('800.00'),
            sequence_order=1,
        )
        RiceMillAppointment.objects.create(
            machine=self.rice_mill_machine,
            user=self.member,
            appointment_date=today - timedelta(days=2),
            sacks=3,
            rice_quantity=Decimal('120.00'),
            final_weight=Decimal('100.00'),
            price_per_kg=Decimal('5.00'),
            total_amount=Decimal('500.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE,
            status='confirmed',
        )
        RiceMillAppointment.objects.create(
            machine=self.rice_mill_machine,
            user=self.member,
            appointment_date=today - timedelta(days=1),
            sacks=4,
            rice_quantity=Decimal('160.00'),
            final_weight=Decimal('150.00'),
            price_per_kg=Decimal('5.00'),
            total_amount=Decimal('750.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_MEMBER,
            status='confirmed',
        )
        self.payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('1500.00'),
            amount_received=Decimal('2000.00'),
            change_given=Decimal('500.00'),
            status='completed',
            processed_by=self.admin,
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.recent_rental.id,
        )
        self.maintenance = Maintenance.objects.create(
            machine=self.recent_machine,
            description='Engine tune-up and replacement parts',
            maintenance_type='corrective',
            start_date=timezone.now() - timedelta(days=3),
            actual_completion_date=timezone.now() - timedelta(days=2),
            labor_cost=Decimal('150.00'),
            other_cost=Decimal('50.00'),
            technician=self.admin,
            repair_summary='Replaced worn bearings and adjusted engine timing.',
            completion_notes='Machine is operational after testing.',
            status='completed',
            created_by=self.admin,
        )
        MaintenancePartUsed.objects.create(
            maintenance_record=self.maintenance,
            part_name='Bearing',
            quantity=2,
            unit_price=Decimal('100.00'),
        )
        self.maintenance.sync_completion_totals()
        self.repeat_maintenance = Maintenance.objects.create(
            machine=self.recent_machine,
            description='Engine tune-up and replacement parts',
            maintenance_type='corrective',
            start_date=timezone.now() - timedelta(days=8),
            actual_completion_date=timezone.now() - timedelta(days=6),
            labor_cost=Decimal('80.00'),
            other_cost=Decimal('20.00'),
            technician=self.admin,
            repair_summary='Repeated corrective work after another vibration issue.',
            completion_notes='Observed similar wear pattern.',
            status='completed',
            created_by=self.admin,
        )
        MaintenancePartUsed.objects.create(
            maintenance_record=self.repeat_maintenance,
            part_name='Seal Kit',
            quantity=1,
            unit_price=Decimal('60.00'),
        )
        self.repeat_maintenance.sync_completion_totals()
        self.client.force_login(self.admin)

    def test_remaining_report_pages_load(self):
        report_urls = [
            'reports:index',
            'reports:rental_report',
            'reports:harvest_report',
            'reports:rice_sales_report',
            'reports:financial_summary',
            'reports:machine_usage_report',
            'reports:membership_report',
            'reports:sector_comparison',
        ]

        for url_name in report_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_period_report_routes_are_removed(self):
        removed_routes = [
            'reports:weekly_report',
            'reports:monthly_report',
            'reports:yearly_report',
        ]

        for url_name in removed_routes:
            with self.subTest(url_name=url_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(url_name)

    def test_reports_overview_sidebar_uses_updated_menu(self):
        response = self.client.get(reverse('reports:index'))

        self.assertContains(response, 'Reports Overview')
        self.assertNotContains(response, 'Weekly Report')
        self.assertNotContains(response, 'Monthly Report')
        self.assertNotContains(response, 'Yearly Report')

    def test_filtered_rental_excel_export_contains_only_filtered_rows_and_logo(self):
        response = self.client.get(reverse('reports:export_rental_report_excel'), {'date_range': '1_week'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        workbook = ZipFile(BytesIO(response.content))
        self.assertIn('xl/media/logo.png', workbook.namelist())
        sheet_xml = workbook.read('xl/worksheets/sheet1.xml').decode('utf-8')

        self.assertIn('Recent Tractor', sheet_xml)
        self.assertNotIn('Old Tractor', sheet_xml)
        self.assertIn('1 Week', sheet_xml)

    def test_report_excel_exports_use_distinct_theme_colors(self):
        rental_response = self.client.get(reverse('reports:export_rental_report_excel'), {'date_range': '1_week'})
        membership_response = self.client.get(reverse('reports:export_membership_report_excel'))

        rental_workbook = ZipFile(BytesIO(rental_response.content))
        membership_workbook = ZipFile(BytesIO(membership_response.content))

        rental_styles = rental_workbook.read('xl/styles.xml').decode('utf-8')
        membership_styles = membership_workbook.read('xl/styles.xml').decode('utf-8')

        self.assertIn('FF2563EB', rental_styles)
        self.assertIn('FF166534', membership_styles)
        self.assertNotEqual(rental_styles, membership_styles)

    def test_filtered_rental_pdf_export_includes_formatted_header_meta(self):
        response = self.client.get(reverse('reports:export_rental_report_pdf'), {'date_range': '1_week'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(b'Printed:', response.content)
        self.assertIn(b'Total Results:', response.content)
        self.assertIn(b'Rental Transactions Filtered Report', response.content)

    def test_harvest_report_uses_only_designated_harvest_milling_user(self):
        RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
        )

        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bufia_milling']['source_label'], 'BUFIA Rice Share')
        self.assertEqual(response.context['bufia_milling']['total_milled_weight'], Decimal('100.00'))
        self.assertEqual(response.context['bufia_milling']['total_milling_cost'], Decimal('500.00'))
        self.assertEqual(response.context['bufia_milling']['completed_appointments'], 1)
        self.assertEqual(response.context['rice_inventory']['milling_cost_per_sack'], Decimal('250.00'))
        self.assertEqual(response.context['rice_inventory']['cost_of_sold_rice'], Decimal('500.00'))
        self.assertEqual(response.context['rice_inventory']['net_income_from_sold_rice'], Decimal('2400.00'))
        self.assertContains(response, 'Milling source')
        self.assertContains(response, 'Rice Sales Income')

    def test_harvest_report_shows_member_and_delivery_filters(self):
        response = self.client.get(reverse('reports:harvest_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Member')
        self.assertContains(response, 'Delivery Status')
        self.assertContains(response, 'All Members')
        self.assertContains(response, 'All Delivery Status')

    def test_rice_sales_report_counts_bufia_rice_share_after_final_weight_recorded(self):
        RiceMillAppointment.objects.create(
            machine=self.rice_mill_machine,
            user=self.member,
            appointment_date=timezone.localdate(),
            sacks=2,
            rice_quantity=Decimal('80.00'),
            final_weight=Decimal('70.00'),
            price_per_kg=Decimal('5.00'),
            total_amount=Decimal('350.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE,
            status='paid',
        )

        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bufia_milling']['total_milled_weight'], Decimal('170.00'))
        self.assertEqual(response.context['bufia_milling']['total_milling_cost'], Decimal('850.00'))
        self.assertEqual(response.context['bufia_milling']['completed_appointments'], 2)

    def test_rental_report_toolbar_buttons_render(self):
        response = self.client.get(reverse('reports:rental_report'))

        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Export Excel')
        self.assertContains(response, 'Export PDF')
        self.assertNotContains(response, 'Export CSV')
        self.assertNotContains(response, 'Copy Link')

    def test_admin_payment_toolbar_buttons_render(self):
        response = self.client.get(reverse('admin_payment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Export Excel')
        self.assertContains(response, 'Export PDF')
        self.assertNotContains(response, 'Export CSV')
        self.assertNotContains(response, 'Copy Link')

    def test_admin_payment_filters_match_report_style_actions(self):
        response = self.client.get(reverse('admin_payment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filter Payments')
        self.assertContains(response, 'Apply')
        self.assertContains(response, 'Reset')
        self.assertNotContains(response, 'Clear Filters')

    def test_admin_payment_list_shows_over_counter_columns(self):
        response = self.client.get(reverse('admin_payment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cash / Change')
        self.assertContains(response, 'Change:')
        self.assertContains(response, 'Over the Counter')

    def test_financial_summary_uses_revenue_only_view(self):
        response = self.client.get(reverse('reports:financial_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Revenue')
        self.assertContains(response, 'Refunded')
        self.assertContains(response, 'Net Revenue')
        self.assertNotContains(response, 'Cash Received')
        self.assertNotContains(response, 'Change Given')
        self.assertNotContains(response, 'Received: PHP')
        self.assertNotContains(response, 'Change: PHP')

    def test_admin_payment_detail_can_record_partial_refund(self):
        response = self.client.post(
            reverse('admin_payment_detail', args=[self.payment.id]),
            {
                'amount': '300.00',
                'method': 'cash',
                'reason': 'Service adjustment approved by admin.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        refund = Refund.objects.get(payment=self.payment)
        self.assertEqual(refund.amount, Decimal('300.00'))
        self.assertEqual(refund.method, 'cash')
        self.assertEqual(refund.refunded_by, self.admin)
        self.assertEqual(self.payment.status, 'completed')
        self.assertTrue(self.payment.can_accept_refunds)
        self.assertContains(response, 'Refund recorded successfully.')
        self.assertContains(response, 'Partially Refunded')
        self.assertContains(response, f'{self.payment.currency} 300.00')

    def test_admin_payment_detail_locks_payment_when_fully_refunded(self):
        first_response = self.client.post(
            reverse('admin_payment_detail', args=[self.payment.id]),
            {
                'amount': '300.00',
                'method': 'cash',
                'reason': 'First refund recorded.',
            },
            follow=True,
        )

        self.assertEqual(first_response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'completed')
        self.assertTrue(self.payment.can_accept_refunds)

        second_response = self.client.post(
            reverse('admin_payment_detail', args=[self.payment.id]),
            {
                'amount': '1200.00',
                'method': 'cash',
                'reason': 'Finalize the refund.',
            },
            follow=True,
        )

        self.assertEqual(second_response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'refunded')
        self.assertFalse(self.payment.can_accept_refunds)
        self.assertEqual(Refund.objects.filter(payment=self.payment, status='refunded').count(), 2)

        third_response = self.client.post(
            reverse('admin_payment_detail', args=[self.payment.id]),
            {
                'amount': '100.00',
                'method': 'cash',
                'reason': 'This extra refund should be blocked.',
            },
            follow=True,
        )

        self.assertEqual(third_response.status_code, 200)
        self.assertEqual(Refund.objects.filter(payment=self.payment, status='refunded').count(), 2)
        self.assertContains(third_response, 'This payment cannot accept additional refunds.')

    def test_admin_payment_search_matches_gateway_reference(self):
        online_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('800.00'),
            currency='PHP',
            status='pending',
            payment_provider='paymongo',
            stripe_session_id='cs_test_search_payment_001',
            stripe_payment_intent_id='pi_test_search_payment_001',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )

        response = self.client.get(reverse('admin_payment_list'), {'search': 'pi_test_search_payment_001'})

        self.assertEqual(response.status_code, 200)
        page_payments = list(response.context['page_obj'].object_list)
        self.assertEqual([payment.id for payment in page_payments], [online_payment.id])

    def test_admin_payment_list_shows_membership_follow_up_actions(self):
        membership_payment = Payment.objects.create(
            user=self.member,
            payment_type='membership',
            amount=Decimal('500.00'),
            currency='PHP',
            status='pending',
            payment_provider='manual',
            content_type=ContentType.objects.get_for_model(MembershipApplication),
            object_id=self.application.id,
        )

        response = self.client.get(reverse('admin_payment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('review_application', args=[self.application.pk]))
        self.assertContains(response, reverse('mark_membership_paid', args=[self.member.pk]))
        self.assertContains(response, membership_payment.get_payment_type_display())

    def test_admin_payment_detail_shows_membership_related_service_context(self):
        membership_payment = Payment.objects.create(
            user=self.member,
            payment_type='membership',
            amount=Decimal('500.00'),
            currency='PHP',
            status='pending',
            payment_provider='manual',
            content_type=ContentType.objects.get_for_model(MembershipApplication),
            object_id=self.application.id,
        )

        response = self.client.get(reverse('admin_payment_detail', args=[membership_payment.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Related Service')
        self.assertContains(response, self.application.workflow_status_label)
        self.assertContains(response, reverse('review_application', args=[self.application.pk]))
        self.assertContains(response, 'Mark Membership Paid')

    def test_financial_summary_subtracts_refunds_from_net_revenue(self):
        Refund.objects.create(
            payment=self.payment,
            amount=Decimal('250.00'),
            method='cash',
            reason='Refund for overcharge.',
            status='refunded',
            refunded_by=self.admin,
            refunded_at=timezone.now(),
        )

        response = self.client.get(reverse('reports:financial_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PHP 250.00')
        self.assertContains(response, 'PHP 2850.00')

    def test_rental_report_shows_refund_status_after_refund_processing(self):
        Refund.objects.create(
            payment=self.payment,
            amount=Decimal('250.00'),
            method='cash',
            reason='Refund for overcharge.',
            status='refunded',
            refunded_by=self.admin,
            refunded_at=timezone.now(),
        )

        response = self.client.get(reverse('reports:rental_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Partially Refunded')
        self.assertContains(response, 'Refunded: PHP 250.00')

    def test_financial_summary_can_filter_package_transactions(self):
        package_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('800.00'),
            status='completed',
            payment_provider='manual',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )

        response = self.client.get(
            reverse('reports:financial_summary'),
            {
                'transaction_type': 'package_rental',
                'availing_type': 'package',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Package Rental')
        self.assertContains(response, self.rental_package.package_name)
        self.assertContains(response, package_payment.internal_transaction_id)
        self.assertNotContains(response, self.payment.internal_transaction_id)

    def test_financial_summary_stats_follow_package_transaction_filter(self):
        package_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('800.00'),
            status='completed',
            payment_provider='manual',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )
        MembershipApplication.objects.create(
            user=User.objects.create_user(
                username='package-filter-legacy-member',
                email='package-filter-legacy-member@example.com',
                password='testpass123',
            ),
            payment_method='face_to_face',
            payment_status='paid',
            payment_date=timezone.now(),
        )
        RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
            paid_at=timezone.now(),
            processed_by=self.admin,
        )

        response = self.client.get(
            reverse('reports:financial_summary'),
            {
                'transaction_type': 'package_rental',
                'availing_type': 'package',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, package_payment.internal_transaction_id)
        self.assertEqual(response.context['stats']['rental_income'], Decimal('800.00'))
        self.assertEqual(response.context['stats']['membership_income'], Decimal('0.00'))
        self.assertEqual(response.context['stats']['rice_sales_income'], Decimal('0.00'))
        self.assertEqual(response.context['service_income'], Decimal('0.00'))
        self.assertEqual(response.context['gross_revenue'], Decimal('800.00'))

    def test_financial_summary_stats_follow_payment_method_filter(self):
        gcash_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('800.00'),
            status='completed',
            payment_provider='paymongo',
            stripe_payment_intent_id='pi_financial_filter_001',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )

        response = self.client.get(
            reverse('reports:financial_summary'),
            {
                'payment_method': 'gcash',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, gcash_payment.internal_transaction_id)
        self.assertNotContains(response, self.payment.internal_transaction_id)
        self.assertEqual(response.context['stats']['rental_income'], Decimal('800.00'))
        self.assertEqual(response.context['stats']['membership_income'], Decimal('0.00'))
        self.assertEqual(response.context['stats']['rice_sales_income'], Decimal('0.00'))
        self.assertEqual(response.context['service_income'], Decimal('0.00'))
        self.assertEqual(response.context['gross_revenue'], Decimal('800.00'))

    def test_admin_payment_refund_updates_rental_follow_up_status(self):
        self.recent_rental.follow_up_action = 'refund_requested'
        self.recent_rental.save(update_fields=['follow_up_action', 'updated_at'])

        response = self.client.post(
            reverse('admin_payment_detail', args=[self.payment.id]),
            {
                'amount': '200.00',
                'method': 'cash',
                'reason': 'Approved refund.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.recent_rental.refresh_from_db()
        self.assertEqual(self.recent_rental.follow_up_action, 'refund_processed')

    def test_financial_summary_includes_rice_sales_and_legacy_membership_transactions(self):
        legacy_member = User.objects.create_user(
            username='legacy-member',
            email='legacy-member@example.com',
            password='testpass123',
            first_name='Legacy',
            last_name='Member',
        )
        legacy_application = MembershipApplication.objects.create(
            user=legacy_member,
            payment_method='face_to_face',
            payment_status='paid',
            payment_date=timezone.now(),
        )
        rice_sale = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
            paid_at=timezone.now(),
            processed_by=self.admin,
        )

        response = self.client.get(reverse('reports:financial_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rice Sales')
        self.assertContains(response, 'PHP 2400.00')
        self.assertContains(response, legacy_application.user.get_full_name())
        self.assertContains(response, f'BUFIA-MEM-{legacy_application.pk:05d}')
        self.assertContains(response, rice_sale.reference_number)
        payment_types = [item.payment_type_display for item in response.context['payments']]
        self.assertIn('Membership Fee', payment_types)
        self.assertIn('Rice Sale', payment_types)

    def test_financial_summary_custom_range_uses_payment_transaction_dates_for_rental_income(self):
        today = timezone.localdate()
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()

        out_of_range_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('3200.00'),
            status='completed',
            processed_by=self.admin,
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.recent_rental.id,
        )
        Payment.objects.filter(pk=out_of_range_payment.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        in_range_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('900.00'),
            status='completed',
            processed_by=self.admin,
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )
        Payment.objects.filter(pk=in_range_payment.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        Rental.objects.filter(pk=self.package_rental.pk).update(
            created_at=timezone.now() - timedelta(days=45)
        )

        response = self.client.get(
            reverse('reports:financial_summary'),
            {
                'date_range': 'all',
                'start_date': start_date,
                'end_date': end_date,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Range')
        self.assertContains(response, 'PHP 2400.00')
        self.assertContains(response, in_range_payment.internal_transaction_id)
        self.assertNotContains(response, out_of_range_payment.internal_transaction_id)

    def test_financial_summary_uses_paid_at_for_completed_package_payments(self):
        today = timezone.localdate()
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()

        package_payment = Payment.objects.create(
            user=self.member,
            payment_type='rental',
            amount=Decimal('800.00'),
            status='pending',
            payment_provider='manual',
            content_type=ContentType.objects.get_for_model(Rental),
            object_id=self.package_rental.id,
        )
        Payment.objects.filter(pk=package_payment.pk).update(
            created_at=timezone.now() - timedelta(days=30),
            status='completed',
            paid_at=timezone.now() - timedelta(days=1),
            amount_received=Decimal('800.00'),
            change_given=Decimal('0.00'),
            processed_by=self.admin,
        )

        response = self.client.get(
            reverse('reports:financial_summary'),
            {
                'date_range': 'all',
                'start_date': start_date,
                'end_date': end_date,
                'transaction_type': 'package_rental',
                'availing_type': 'package',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, package_payment.internal_transaction_id)
        self.assertContains(response, 'Package Rental')
        self.assertContains(response, 'Over the Counter')

    def test_reports_overview_counts_completed_transactions_beyond_payment_table(self):
        MembershipApplication.objects.create(
            user=User.objects.create_user(
                username='legacy-overview-member',
                email='legacy-overview-member@example.com',
                password='testpass123',
            ),
            payment_method='face_to_face',
            payment_status='paid',
            payment_date=timezone.now(),
        )
        RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('900.00'),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
            paid_at=timezone.now(),
            processed_by=self.admin,
        )

        response = self.client.get(reverse('reports:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['overview_stats']['completed_transactions'], 3)
        self.assertContains(response, 'Completed Transactions')

    def test_machine_usage_report_shows_acquisition_and_net_earnings(self):
        response = self.client.get(reverse('reports:machine_usage_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acquisition Cost')
        self.assertContains(response, 'Net Profit')
        self.assertContains(response, 'Kubota')
        self.assertContains(response, 'Cost PHP 1000.00')
        self.assertContains(response, 'Operating PHP 560.00')
        self.assertContains(response, 'Net PHP 940.00')
        self.assertContains(response, '94.00%')
        self.assertContains(response, 'View Details')

    def test_financial_summary_shows_machine_profitability_cards(self):
        response = self.client.get(reverse('reports:financial_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machine Revenue')
        self.assertContains(response, 'Machine Acquisition Cost')
        self.assertContains(response, 'Machine Operating Cost')
        self.assertContains(response, 'Machine Net Profit')
        self.assertContains(response, 'PHP 3100.00')
        self.assertContains(response, 'PHP 1800.00')
        self.assertContains(response, 'PHP 560.00')
        self.assertEqual(response.context['stats']['machine_net_earnings'], Decimal('3790.00'))

    def test_machine_usage_detail_shows_maintenance_cost_breakdown(self):
        response = self.client.get(reverse('reports:machine_usage_detail', args=[self.recent_machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machine ROI Detail')
        self.assertContains(response, 'Machine Summary')
        self.assertContains(response, 'ROI Snapshot')
        self.assertNotContains(response, 'Expense Summary')
        self.assertNotContains(response, 'Maintenance Timeline')
        self.assertNotContains(response, 'Recurring Repair Alerts')
        self.assertNotContains(response, 'Revenue Breakdown')
        self.assertContains(response, 'Recent Rental Income Records')
        self.assertNotContains(response, 'Recent Rice Mill Income Records')
        self.assertNotContains(response, 'Recent Dryer Income Records')
        self.assertContains(response, 'Operating Expenses')
        self.assertContains(response, 'Recovery Status')
        self.assertContains(response, 'Payback Progress')
        self.assertContains(response, 'Remaining to Recover')
        self.assertContains(response, 'Parts Cost:')
        self.assertContains(response, 'Labor Cost:')
        self.assertContains(response, 'Other Cost:')
        self.assertContains(response, 'Engine tune-up and replacement parts')
        self.assertContains(response, 'Replaced worn bearings and adjusted engine timing.')
        self.assertNotContains(response, reverse('machines:maintenance_detail', args=[self.maintenance.pk]))
        self.assertContains(response, 'PHP 200.00')
        self.assertContains(response, 'PHP 150.00')
        self.assertContains(response, 'PHP 50.00')
        self.assertContains(response, 'PHP 940.00')
        self.assertContains(response, '94.00%')
        self.assertContains(response, 'Recovering')
        self.assertContains(response, '94.00% recovered')
        self.assertContains(response, 'PHP 940.00 / PHP 1000.00')
        self.assertContains(response, 'PHP 60.00')

    def test_machine_usage_report_shows_clean_profit_after_diesel_and_maintenance(self):
        self.recent_rental.diesel_consumed = Decimal('18.50')
        self.recent_rental.diesel_cost = Decimal('300.00')
        self.recent_rental.save(update_fields=['diesel_consumed', 'diesel_cost'])

        response = self.client.get(reverse('reports:machine_usage_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clean Profit')
        self.assertContains(response, '18.50 L diesel')
        self.assertContains(response, 'Maint. PHP 560.00')
        self.assertContains(response, 'PHP 640.00')

    def test_machine_usage_detail_shows_diesel_cost_in_clean_profit_breakdown(self):
        self.recent_rental.diesel_consumed = Decimal('18.50')
        self.recent_rental.diesel_cost = Decimal('300.00')
        self.recent_rental.save(update_fields=['diesel_consumed', 'diesel_cost'])

        response = self.client.get(reverse('reports:machine_usage_detail', args=[self.recent_machine.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Diesel Jobs')
        self.assertContains(response, 'Diesel Consumed')
        self.assertContains(response, 'Diesel Cost')
        self.assertContains(response, '18.50 L')
        self.assertContains(response, 'PHP 300.00')
        self.assertContains(response, 'PHP 640.00')

    def test_rental_report_links_to_payment_details_without_cash_breakdown(self):
        response = self.client.get(reverse('reports:rental_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Payment')
        self.assertContains(response, reverse('admin_payment_detail', args=[self.payment.id]))
        self.assertContains(response, 'Over the Counter')
        self.assertNotContains(response, 'Received PHP 2000.00 | Change PHP 500.00')

    def test_financial_report_toolbar_and_filters_render_consistently(self):
        response = self.client.get(reverse('reports:financial_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Export Excel')
        self.assertContains(response, 'Export PDF')
        self.assertNotContains(response, 'Print Report')
        self.assertContains(response, 'Filter Financial Records')
        self.assertContains(response, 'Apply')
        self.assertContains(response, 'Reset')

    def test_core_reports_use_unified_cards_and_tables(self):
        report_urls = [
            'reports:financial_summary',
            'reports:harvest_report',
            'reports:machine_usage_report',
            'reports:membership_report',
        ]

        for url_name in report_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'page-stat-card')
                self.assertContains(response, 'page-table-card')
                self.assertContains(response, 'report-compact-table')
                self.assertContains(response, 'page-filter-actions')

    def test_membership_report_shows_view_proof_action(self):
        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Proof')

    def test_membership_report_uses_masterlist_style_print_flow(self):
        response = self.client.get(reverse('reports:membership_report'), {
            'filter': 'inactive',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '>Preview</a>', html=False)
        self.assertContains(response, 'triggerMembershipReportPrintReport();')
        self.assertContains(response, 'Print Report')
        self.assertContains(response, 'BUFIA Membership Report')
        self.assertContains(response, '<section class="membership-print-sheet print-area" id="membership-print-report">', html=False)

    def test_membership_report_excludes_admin_accounts_from_member_list(self):
        admin_member = User.objects.create_superuser(
            username='membership-admin-hidden',
            email='membership-admin-hidden@example.com',
            password='testpass123',
        )
        admin_member.first_name = 'Hidden'
        admin_member.last_name = 'Admin'
        admin_member.membership_form_submitted = True
        admin_member.is_verified = True
        admin_member.save(update_fields=['first_name', 'last_name', 'membership_form_submitted', 'is_verified'])

        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'membership-admin-hidden')
        self.assertNotContains(response, 'Hidden Admin')

    def test_membership_report_filters_by_membership_submission_date(self):
        today = timezone.localdate()
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()

        self.member.date_joined = timezone.now() - timedelta(days=120)
        self.member.save(update_fields=['date_joined'])
        self.application.submission_date = today - timedelta(days=2)
        self.application.save(update_fields=['submission_date'])

        outside_member = User.objects.create_user(
            username='outside-window-member',
            email='outside-window@example.com',
            password='testpass123',
            first_name='Outside',
            last_name='Window',
            role=User.REGULAR_USER,
            membership_form_submitted=True,
        )
        outside_member.date_joined = timezone.now() - timedelta(days=1)
        outside_member.save(update_fields=['date_joined'])
        MembershipApplication.objects.create(
            user=outside_member,
            submission_date=today - timedelta(days=60),
            is_approved=True,
            payment_status='pending',
        )

        response = self.client.get(
            reverse('reports:membership_report'),
            {
                'filter': 'all',
                'date_range': 'custom',
                'start_date': start_date,
                'end_date': end_date,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Submitted')
        self.assertContains(response, self.member.get_full_name())
        self.assertNotContains(response, outside_member.get_full_name())

    def test_membership_report_inactive_filter_includes_deactivated_members(self):
        inactive_member = User.objects.create_user(
            username='hazel-inactive',
            email='hazel@example.com',
            password='testpass123',
            first_name='Hazel',
            last_name='Inactive',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
            is_active=False,
        )
        MembershipApplication.objects.create(
            user=inactive_member,
            is_approved=True,
            payment_status='pending',
        )
        not_submitted_member = User.objects.create_user(
            username='not-submitted-member',
            email='not-submitted@example.com',
            password='testpass123',
            first_name='No',
            last_name='Submission',
            role=User.REGULAR_USER,
            membership_form_submitted=False,
        )

        response = self.client.get(
            reverse('reports:membership_report'),
            {'filter': 'inactive'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, inactive_member.get_full_name())
        self.assertContains(response, not_submitted_member.get_full_name())
        self.assertNotContains(response, self.member.get_full_name())
        self.assertContains(response, '<span class="badge bg-secondary">Inactive</span>', html=False)
        self.assertContains(response, '<td class="col-status">', html=False)

    def test_membership_pdf_export_uses_membership_submission_date_filters(self):
        today = timezone.localdate()
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()

        self.member.date_joined = timezone.now() - timedelta(days=120)
        self.member.save(update_fields=['date_joined'])
        self.application.submission_date = today - timedelta(days=2)
        self.application.save(update_fields=['submission_date'])

        outside_member = User.objects.create_user(
            username='outside-window-export-member',
            email='outside-window-export@example.com',
            password='testpass123',
            first_name='Export',
            last_name='Outside',
            role=User.REGULAR_USER,
            membership_form_submitted=True,
        )
        outside_member.date_joined = timezone.now() - timedelta(days=1)
        outside_member.save(update_fields=['date_joined'])
        MembershipApplication.objects.create(
            user=outside_member,
            submission_date=today - timedelta(days=60),
            is_approved=True,
            payment_status='pending',
        )

        response = self.client.get(
            reverse('reports:export_membership_report_pdf'),
            {
                'filter': 'all',
                'date_range': 'custom',
                'start_date': start_date,
                'end_date': end_date,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(b'Submitted', response.content)
        self.assertIn(self.member.get_full_name().encode(), response.content)
        self.assertNotIn(outside_member.get_full_name().encode(), response.content)

    def test_membership_printable_exports_show_inactive_status(self):
        inactive_member = User.objects.create_user(
            username='printable-inactive',
            email='printable-inactive@example.com',
            password='testpass123',
            first_name='Printable',
            last_name='Inactive',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
            is_active=False,
        )
        MembershipApplication.objects.create(
            user=inactive_member,
            is_approved=True,
            payment_status='pending',
        )

        excel_response = self.client.get(
            reverse('reports:export_membership_report_excel'),
            {'filter': 'inactive'},
        )

        self.assertEqual(excel_response.status_code, 200)
        self.assertEqual(
            excel_response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        workbook = ZipFile(BytesIO(excel_response.content))
        sheet_xml = workbook.read('xl/worksheets/sheet1.xml').decode('utf-8')
        self.assertIn('Printable Inactive', sheet_xml)
        self.assertIn('Inactive', sheet_xml)

        pdf_response = self.client.get(
            reverse('reports:export_membership_report_pdf'),
            {'filter': 'inactive'},
        )

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
        self.assertIn(b'Printable Inactive', pdf_response.content)
        self.assertIn(b'Inactive', pdf_response.content)

    def test_membership_report_shows_view_info_action_and_modal(self):
        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Info')
        self.assertContains(response, 'Deactivate')
        self.assertContains(response, 'Membership Information')
        self.assertContains(response, 'id="membershipInfoModal" aria-hidden="true" hidden', html=False)
        self.assertContains(
            response,
            reverse('view_membership_info_user', args=[self.member.id]),
        )
        self.assertContains(
            response,
            reverse('deactivate_user', args=[self.member.id]),
        )

    def test_membership_report_modal_includes_valid_id_document(self):
        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'National ID')
        self.assertContains(response, 'data-valid-id-exists="true"', html=False)
        self.assertContains(response, 'data-valid-id-url="', html=False)

    def test_membership_report_shows_upload_proof_action_when_file_missing(self):
        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload Proof')
        self.assertContains(
            response,
            reverse('reports:membership_proof_detail', args=[self.application_without_proof.pk]),
        )

    def test_membership_report_shows_fix_missing_proof_action_when_file_path_is_stale(self):
        response = self.client.get(reverse('reports:membership_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fix Missing Proof')
        self.assertContains(
            response,
            reverse('reports:membership_proof_detail', args=[self.application_with_missing_proof.pk]),
        )

    def test_review_application_shows_upload_form_when_proof_missing(self):
        response = self.client.get(reverse('review_application', args=[self.application_without_proof.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save Uploaded Proof')
        self.assertContains(response, 'Land Title / Tax Declaration Upload')

    def test_review_application_can_save_missing_proof(self):
        response = self.client.post(
            reverse('review_application', args=[self.application_without_proof.pk]),
            {
                'proof_upload_submit': '1',
                'land_proof_notes': 'Admin uploaded the missing tenancy certificate.',
                'land_proof_documents': [
                    SimpleUploadedFile(
                        'tenancy-proof.jpg',
                        b'proof-image-bytes',
                        content_type='image/jpeg',
                    )
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('review_application', args=[self.application_without_proof.pk]))

        self.application_without_proof.refresh_from_db()
        self.assertTrue(bool(self.application_without_proof.land_proof_document))
        self.assertEqual(
            self.application_without_proof.land_proof_notes,
            'Admin uploaded the missing tenancy certificate.',
        )

    def test_membership_proof_detail_page_loads(self):
        response = self.client.get(reverse('reports:membership_proof_detail', args=[self.application.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ownership Proof')
        self.assertContains(response, self.application.land_proof_notes)
        self.assertContains(response, self.application.land_proof_filename)

    def test_membership_proof_detail_shows_upload_form_when_proof_missing(self):
        response = self.client.get(reverse('reports:membership_proof_detail', args=[self.application_without_proof.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save Uploaded Proof')
        self.assertContains(response, 'Land Title / Tax Declaration Upload')
        self.assertContains(response, 'name="land_proof_documents"', count=2)

    def test_membership_proof_detail_cleans_missing_proof_records_and_reopens_upload_slots(self):
        response = self.client.get(reverse('reports:membership_proof_detail', args=[self.application_with_missing_proof.pk]))

        self.assertEqual(response.status_code, 200)
        self.application_with_missing_proof.refresh_from_db()
        self.assertEqual(self.application_with_missing_proof.land_proof_count, 0)
        self.assertFalse(self.application_with_missing_proof.land_proof_document)
        self.assertContains(response, 'No file uploaded yet')
        self.assertContains(response, 'name="land_proof_documents"', count=2)
        self.assertNotContains(response, 'Missing file')

    def test_membership_proof_detail_can_save_missing_proof(self):
        response = self.client.post(
            reverse('reports:membership_proof_detail', args=[self.application_without_proof.pk]),
            {
                'proof_upload_submit': '1',
                'land_proof_notes': 'Admin uploaded the missing tenancy certificate.',
                'land_proof_documents': [
                    SimpleUploadedFile(
                        'tenancy-proof.jpg',
                        b'proof-image-bytes',
                        content_type='image/jpeg',
                    )
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('reports:membership_proof_detail', args=[self.application_without_proof.pk]),
        )

        self.application_without_proof.refresh_from_db()
        self.assertTrue(bool(self.application_without_proof.land_proof_document))
        self.assertEqual(
            self.application_without_proof.land_proof_notes,
            'Admin uploaded the missing tenancy certificate.',
        )

    def test_membership_proof_detail_appends_new_proof_to_existing_list(self):
        response = self.client.post(
            reverse('reports:membership_proof_detail', args=[self.application.pk]),
            {
                'proof_upload_submit': '1',
                'land_proof_notes': 'Added a second supporting proof.',
                'land_proof_documents': [
                    SimpleUploadedFile(
                        'second-proof.pdf',
                        b'proof-pdf-bytes',
                        content_type='application/pdf',
                    )
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('reports:membership_proof_detail', args=[self.application.pk]))

        self.application.refresh_from_db()
        self.assertEqual(self.application.land_proof_count, 2)
        self.assertEqual(self.application.proof_documents.count(), 2)
        proof_names = [proof.filename for proof in self.application.proof_documents.all()]
        self.assertEqual(len(proof_names), 2)
        self.assertTrue(proof_names[0].startswith('membership-proof'))
        self.assertTrue(proof_names[1].startswith('second-proof'))

    def test_membership_proof_detail_hides_upload_inputs_when_two_files_already_exist(self):
        self.application.proof_documents.create(
            document=SimpleUploadedFile(
                'first-proof.jpg',
                b'proof-jpg-bytes',
                content_type='image/jpeg',
            ),
            display_order=0,
        )
        self.application.proof_documents.create(
            document=SimpleUploadedFile(
                'second-proof.pdf',
                b'proof-pdf-bytes',
                content_type='application/pdf',
            ),
            display_order=1,
        )

        response = self.client.get(reverse('reports:membership_proof_detail', args=[self.application.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload Complete')
        self.assertContains(response, 'Two land title or tax declaration files are already saved for this application.')
        self.assertContains(response, 'Save Notes')
        self.assertNotContains(response, 'Upload Full')
        self.assertNotContains(response, 'Maximum of 2 land title or tax declaration files already uploaded.')
        self.assertNotContains(response, 'name="land_proof_documents"')

    def test_membership_proof_detail_rejects_more_than_two_files(self):
        response = self.client.post(
            reverse('reports:membership_proof_detail', args=[self.application_without_proof.pk]),
            {
                'proof_upload_submit': '1',
                'land_proof_notes': 'Too many proofs uploaded.',
                'land_proof_documents': [
                    SimpleUploadedFile('proof-1.jpg', b'proof-1', content_type='image/jpeg'),
                    SimpleUploadedFile('proof-2.png', b'proof-2', content_type='image/png'),
                    SimpleUploadedFile('proof-3.pdf', b'proof-3', content_type='application/pdf'),
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload up to 2 land title or tax declaration files only.')

    def test_filtered_admin_payment_excel_export_returns_xlsx(self):
        response = self.client.get(reverse('export_payments_excel'), {'status': 'completed'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        workbook = ZipFile(BytesIO(response.content))
        sheet_xml = workbook.read('xl/worksheets/sheet1.xml').decode('utf-8')

        self.assertIn('Payment Transactions Filtered Report', sheet_xml)
        self.assertIn('Recent Member', sheet_xml)
        self.assertIn('Completed', sheet_xml)

    def test_filtered_admin_payment_pdf_export_returns_pdf_header(self):
        response = self.client.get(reverse('export_payments_pdf'), {'status': 'completed'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(b'Bayawan United Farmers Irrigation Association Incorporated', response.content)
        self.assertIn(b'Payment Transactions Filtered Report', response.content)

    def test_filtered_admin_payment_pdf_preview_returns_inline_header(self):
        response = self.client.get(reverse('export_payments_pdf'), {'status': 'completed', 'preview': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))

    def test_rental_report_snapshot_shows_selected_labels(self):
        today = timezone.localdate()
        start_date = (today - timedelta(days=2)).isoformat()
        end_date = today.isoformat()
        response = self.client.get(
            reverse('reports:rental_report'),
            {
                'date_range': 'custom',
                'start_date': start_date,
                'end_date': end_date,
                'machine': str(self.recent_machine.id),
                'member': str(self.member.id),
                'status': 'completed',
            },
        )

        self.assertContains(response, self.recent_machine.name)
        self.assertContains(response, self.member.get_full_name())
        self.assertContains(response, 'Completed')

    def test_rental_report_can_filter_package_availing(self):
        response = self.client.get(
            reverse('reports:rental_report'),
            {
                'availing_type': 'package',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Package Availing')
        self.assertContains(response, self.rental_package.package_name)
        self.assertContains(response, 'View Package')

    def test_rental_report_snapshot_shows_availing_type_label(self):
        response = self.client.get(
            reverse('reports:rental_report'),
            {
                'availing_type': 'direct',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Availing Type')
        self.assertContains(response, 'Direct Rental')

    def test_filtered_rental_pdf_export_returns_pdf_header(self):
        response = self.client.get(reverse('reports:export_rental_report_pdf'), {'date_range': '1_week'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(b'Bayawan United Farmers Irrigation Association Incorporated', response.content)
        self.assertIn(b'Rental Transactions Filtered Report', response.content)

    def test_filtered_rental_pdf_preview_returns_inline_header(self):
        response = self.client.get(reverse('reports:export_rental_report_pdf'), {'date_range': '1_week', 'preview': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))

    def test_other_export_routes_load(self):
        export_urls = [
            'reports:export_harvest_report_excel',
            'reports:export_harvest_report_pdf',
            'reports:export_financial_report_excel',
            'reports:export_financial_report_pdf',
            'reports:export_machine_usage_report_excel',
            'reports:export_machine_usage_report_pdf',
            'reports:export_membership_report_excel',
            'reports:export_membership_report_pdf',
        ]

        for url_name in export_urls:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name), {'date_range': '1_week'})
                self.assertEqual(response.status_code, 200)


class RiceStoreFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='rice-admin',
            email='rice-admin@example.com',
            password='testpass123',
        )
        self.member = User.objects.create_user(
            username='rice-member',
            email='rice-member@example.com',
            password='testpass123',
            first_name='Rice',
            last_name='Buyer',
            role=User.REGULAR_USER,
            is_verified=True,
            membership_form_submitted=True,
        )
        self.non_member = User.objects.create_user(
            username='not-approved',
            email='not-approved@example.com',
            password='testpass123',
            role=User.REGULAR_USER,
            is_verified=False,
        )
        MembershipApplication.objects.create(
            user=self.member,
            is_approved=True,
            payment_status='paid',
        )
        MembershipApplication.objects.create(
            user=self.non_member,
            is_approved=False,
            payment_status='pending',
        )
        self.machine = Machine.objects.create(
            name='Harvest Tractor',
            machine_type='tractor_4wd',
            description='Machine for rice store tests',
            current_price='1500',
            rental_price_type='in_kind',
            settlement_type='after_harvest',
        )
        Rental.objects.create(
            machine=self.machine,
            user=self.member,
            start_date=timezone.localdate() - timedelta(days=5),
            end_date=timezone.localdate() - timedelta(days=4),
            payment_type='in_kind',
            status='completed',
            workflow_state='completed',
            total_harvest_sacks=Decimal('50.00'),
            bufia_share=Decimal('10.00'),
            member_share=Decimal('40.00'),
            organization_share_required=Decimal('10.00'),
            organization_share_received=Decimal('8.00'),
            settlement_date=timezone.now(),
        )
        self.rice_mill_machine = Machine.objects.create(
            name='Rice Sales Mill',
            machine_type='rice_mill',
            description='Rice mill for rice sales tests',
            current_price='5',
        )
        RiceMillAppointment.objects.create(
            machine=self.rice_mill_machine,
            user=self.member,
            appointment_date=timezone.localdate() - timedelta(days=1),
            sacks=8,
            rice_quantity=Decimal('320.00'),
            final_weight=Decimal('320.00'),
            price_per_kg=Decimal('5.00'),
            total_amount=Decimal('1600.00'),
            payment_method='face_to_face',
            booking_source=RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE,
            status='confirmed',
        )
        self.setting = RiceSaleSetting.get_solo()

    def test_harvest_report_simplifies_summary_and_uses_delivery_totals(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('reports:harvest_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delivery Progress')
        self.assertContains(response, '8.00 sacks')
        self.assertContains(response, '2.00 sacks')
        self.assertContains(response, '80%')
        self.assertContains(response, '0 settled, 1 pending')
        self.assertNotContains(response, 'Averages')
        self.assertNotContains(response, 'Settlement Rule')

    def test_admin_can_update_rice_sale_settings_from_pricing_page(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('reports:rice_sales_pricing'),
            {
                'is_available_for_sale': 'on',
                'current_price_per_sack': '1450.00',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.setting.refresh_from_db()
        self.assertTrue(self.setting.is_available_for_sale)
        self.assertEqual(self.setting.current_price_per_sack, Decimal('1450.00'))
        self.assertContains(response, 'Rice sale availability and pricing were updated.')

    def test_admin_cannot_set_zero_rice_sale_price(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('reports:rice_sales_pricing'),
            {
                'is_available_for_sale': 'on',
                'current_price_per_sack': '0.00',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.current_price_per_sack, Decimal('0.00'))
        self.assertContains(response, 'Price per sack is required and must be greater than zero.')
        self.assertContains(response, 'Change Pricing and Status')

    def test_rice_sales_report_links_to_pricing_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('reports:rice_sales_pricing'))
        self.assertContains(response, 'Change Pricing')
        self.assertContains(response, reverse('reports:rice_sales_stock_movement'))
        self.assertContains(response, 'Stock Movement Log')
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Print')

    def test_rice_sales_stock_movement_page_shows_log_table(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_stock_movement'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock Movement Log')
        self.assertContains(response, 'Back to Rice Sales')
        self.assertContains(response, reverse('reports:rice_sales_order_records'))
        self.assertContains(response, 'Rice Order Records')
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Print')
        self.assertIn('stock_movements', response.context)

    def test_rice_sales_order_records_page_shows_filters_and_table(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_order_records'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rice Order Records')
        self.assertContains(response, 'Back to Stock Movement Log')
        self.assertContains(response, 'Order Status')
        self.assertContains(response, 'Payment Status')
        self.assertContains(response, 'Payment Method')
        self.assertContains(response, 'Preview')
        self.assertContains(response, 'Print')

    def test_approved_member_can_create_pending_gcash_rice_order_and_stock_is_reserved(self):
        self.setting.is_available_for_sale = True
        self.setting.current_price_per_sack = Decimal('1200.00')
        self.setting.save(update_fields=['is_available_for_sale', 'current_price_per_sack', 'updated_at'])

        self.client.force_login(self.member)
        response = self.client.post(
            reverse('reports:rice_store'),
            {
                'rice_type': 'Premium Rice',
                'sacks': '2.00',
                'pickup_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
                'payment_method': 'gcash',
                'notes': 'Pickup on market day',
            },
        )

        self.assertEqual(response.status_code, 302)
        sale = RiceSale.objects.get(buyer=self.member)
        self.assertEqual(sale.rice_type, 'Premium Rice')
        self.assertEqual(sale.sacks, Decimal('2.00'))
        self.assertEqual(sale.price_per_sack, Decimal('1200.00'))
        self.assertEqual(sale.total_amount, Decimal('2400.00'))
        self.assertEqual(sale.payment_status, RiceSale.PAYMENT_STATUS_PENDING)
        self.assertEqual(sale.order_status, RiceSale.ORDER_STATUS_RESERVED)
        self.assertEqual(response['Location'], reverse('create_rice_sale_payment', args=[sale.pk]))
        store_response = self.client.get(reverse('reports:rice_store'))
        self.assertContains(store_response, 'Pay Now')
        self.assertContains(store_response, 'Cancel Order')
        self.assertContains(store_response, 'Waiting for Payment')

    def test_member_can_cancel_unpaid_rice_order_from_store(self):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )
        payment = Payment.objects.create(
            user=self.member,
            payment_type='rice_sale',
            amount=Decimal('2400.00'),
            currency='PHP',
            status='pending',
            payment_provider='paymongo',
            content_type=ContentType.objects.get_for_model(RiceSale),
            object_id=order.pk,
        )

        self.client.force_login(self.member)
        response = self.client.post(
            reverse('reports:rice_store'),
            {
                'action': 'cancel_order',
                'order_id': str(order.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.order_status, RiceSale.ORDER_STATUS_CANCELLED)
        self.assertEqual(payment.status, 'failed')
        self.assertContains(response, 'was cancelled and the reserved stock was released')

    def test_member_cannot_cancel_paid_rice_order_from_store(self):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            amount_paid=Decimal('2400.00'),
            paid_at=timezone.now(),
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )

        self.client.force_login(self.member)
        response = self.client.post(
            reverse('reports:rice_store'),
            {
                'action': 'cancel_order',
                'order_id': str(order.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.order_status, RiceSale.ORDER_STATUS_RESERVED)
        self.assertContains(response, 'Paid rice orders cannot be cancelled here')

    @patch('bufia.views.payment_views._paymongo_is_configured', return_value=True)
    @patch('bufia.views.payment_views.paymongo_create_checkout_session')
    def test_create_rice_sale_payment_redirects_to_paymongo_checkout(self, mock_create_checkout, _mock_is_configured):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )
        mock_create_checkout.return_value = {
            'id': 'cs_paymongo_rice_sale_1',
            'attributes': {
                'checkout_url': 'https://checkout.paymongo.test/rice-sale-1',
            },
        }

        self.client.force_login(self.member)
        response = self.client.get(reverse('create_rice_sale_payment', args=[order.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://checkout.paymongo.test/rice-sale-1')

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(RiceSale),
            object_id=order.pk,
        )
        self.assertEqual(payment.payment_type, 'rice_sale')
        self.assertEqual(payment.payment_provider, 'paymongo')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.stripe_session_id, 'cs_paymongo_rice_sale_1')

    @patch('bufia.views.payment_views._paymongo_is_configured', return_value=True)
    @patch('bufia.views.payment_views.paymongo_retrieve_checkout_session')
    def test_payment_success_marks_rice_sale_paid_but_keeps_pickup_open(self, mock_retrieve_checkout, _mock_is_configured):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )
        payment = Payment.objects.create(
            user=self.member,
            payment_type='rice_sale',
            amount=Decimal('2400.00'),
            currency='PHP',
            status='pending',
            payment_provider='paymongo',
            stripe_session_id='cs_paymongo_rice_sale_2',
            content_type=ContentType.objects.get_for_model(RiceSale),
            object_id=order.pk,
        )
        mock_retrieve_checkout.return_value = {
            'type': 'checkout_session',
            'id': 'cs_paymongo_rice_sale_2',
            'attributes': {
                'payment_intent': {
                    'id': 'pi_paymongo_rice_sale_2',
                    'attributes': {
                        'status': 'succeeded',
                        'payments': [
                            {
                                'id': 'pay_paymongo_rice_sale_2',
                                'attributes': {
                                    'status': 'paid',
                                    'amount': 240000,
                                },
                            }
                        ],
                    },
                },
            },
        }

        self.client.force_login(self.member)
        response = self.client.get(
            reverse('payment_success'),
            {
                'type': 'rice_sale',
                'id': order.pk,
                'transaction_id': payment.internal_transaction_id,
            },
        )

        self.assertRedirects(response, reverse('reports:rice_store'), fetch_redirect_response=False)
        order.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(order.payment_status, RiceSale.PAYMENT_STATUS_PAID)
        self.assertEqual(order.order_status, RiceSale.ORDER_STATUS_RESERVED)
        self.assertEqual(order.amount_paid, Decimal('2400.00'))
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_paymongo_rice_sale_2')
        self.assertEqual(payment.stripe_charge_id, 'pay_paymongo_rice_sale_2')

    def test_admin_can_record_otc_rice_order_payment_from_pickup_queue(self):
        self.setting.is_available_for_sale = True
        self.setting.current_price_per_sack = Decimal('1200.00')
        self.setting.save(update_fields=['is_available_for_sale', 'current_price_per_sack', 'updated_at'])

        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_READY,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('reports:rice_sales_report'),
            {
                'action': 'record_otc_payment',
                'order_id': str(order.id),
                'amount_received': '2500.00',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, RiceSale.PAYMENT_STATUS_PAID)
        self.assertEqual(order.order_status, RiceSale.ORDER_STATUS_CLAIMED)
        self.assertEqual(order.amount_paid, Decimal('2500.00'))
        self.assertEqual(order.change_given, Decimal('100.00'))

    def test_rice_sales_report_shows_exact_amount_due_and_editable_otc_input(self):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_READY,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Exact Amount Due')
        self.assertContains(response, 'Confirm Payment')
        self.assertContains(response, 'Prefilled with the exact amount due. You can edit it before confirming.')
        self.assertContains(response, 'value="2400.00"', html=False)
        self.assertContains(response, f'amount_received_{order.id}')

    def test_rice_sales_report_shows_non_negative_stock_balances_and_pickup_date_fallback(self):
        order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('2450.00'),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
            claimed_at=timezone.now(),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.created_at.strftime('%b %d, %Y'))
        self.assertNotContains(response, 'Not set')
        stock_movements = response.context['stock_movements']
        self.assertTrue(stock_movements)
        self.assertGreaterEqual(min(row['actual_balance'] for row in stock_movements), Decimal('0.00'))
        self.assertGreaterEqual(min(row['reserved_balance'] for row in stock_movements), Decimal('0.00'))

    def test_rice_sales_report_filters_order_records(self):
        matching_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            amount_paid=Decimal('2400.00'),
            paid_at=timezone.now(),
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )
        other_member = User.objects.create_user(
            username='rice-other',
            email='rice-other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='Buyer',
            role=User.REGULAR_USER,
            is_verified=True,
        )
        MembershipApplication.objects.create(
            user=other_member,
            is_approved=True,
            payment_status='paid',
        )
        excluded_order = RiceSale.objects.create(
            buyer=other_member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_READY,
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('reports:rice_sales_report'),
            {
                'member': str(self.member.id),
                'payment_status': RiceSale.PAYMENT_STATUS_PAID,
            },
        )

        self.assertEqual(response.status_code, 200)
        sales_transactions = response.context['sales_transactions']
        self.assertEqual([order.id for order in sales_transactions], [matching_order.id])
        self.assertContains(response, matching_order.reference_number)

    def test_rice_sales_pdf_preview_uses_filtered_orders(self):
        included_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('2.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            amount_paid=Decimal('2400.00'),
            paid_at=timezone.now(),
            order_status=RiceSale.ORDER_STATUS_CLAIMED,
            claimed_at=timezone.now(),
        )
        excluded_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=timezone.localdate() + timedelta(days=1),
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('reports:export_rice_sales_report_pdf'),
            {
                'payment_status': RiceSale.PAYMENT_STATUS_PAID,
                'preview': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline;', response['Content-Disposition'])
        self.assertIn('rice_sales_report_', response['Content-Disposition'])
        self.assertIn(included_order.reference_number.encode('utf-8'), response.content)
        self.assertNotIn(excluded_order.reference_number.encode('utf-8'), response.content)

    def test_overdue_pickup_auto_cancels_only_unpaid_orders(self):
        overdue_date = timezone.localdate() - timedelta(days=2)
        otc_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=overdue_date,
            payment_method=RiceSale.PAYMENT_METHOD_OTC,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_READY,
        )
        unpaid_gcash_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=overdue_date,
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PENDING,
            order_status=RiceSale.ORDER_STATUS_RESERVED,
        )
        paid_gcash_order = RiceSale.objects.create(
            buyer=self.member,
            sacks=Decimal('1.00'),
            price_per_sack=Decimal('1200.00'),
            pickup_date=overdue_date,
            payment_method=RiceSale.PAYMENT_METHOD_GCASH,
            payment_status=RiceSale.PAYMENT_STATUS_PAID,
            amount_paid=Decimal('1200.00'),
            paid_at=timezone.now(),
            order_status=RiceSale.ORDER_STATUS_READY,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('reports:rice_sales_report'))

        self.assertEqual(response.status_code, 200)
        otc_order.refresh_from_db()
        unpaid_gcash_order.refresh_from_db()
        paid_gcash_order.refresh_from_db()

        self.assertEqual(otc_order.order_status, RiceSale.ORDER_STATUS_CANCELLED)
        self.assertEqual(unpaid_gcash_order.order_status, RiceSale.ORDER_STATUS_CANCELLED)
        self.assertEqual(paid_gcash_order.order_status, RiceSale.ORDER_STATUS_READY)
        self.assertContains(response, 'Overdue Pickup')

    def test_non_approved_member_cannot_open_rice_store(self):
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('reports:rice_store'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only approved members can buy BUFIA rice.')
