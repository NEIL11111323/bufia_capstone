import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from bufia.models import Payment
from users.models import MembershipApplication
from django.contrib.auth import get_user_model


User = get_user_model()


@override_settings(
    PAYMONGO_PUBLIC_KEY='pk_test_fake',
    PAYMONGO_SECRET_KEY='sk_test_fake',
    PAYMONGO_WEBHOOK_SECRET='whsk_test_secret',
    PAYMONGO_PAYMENT_METHODS=['gcash'],
)
class PayMongoMembershipFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='paymongo-member',
            email='paymongo-member@example.com',
            password='testpassword123',
            first_name='PayMongo',
            last_name='Member',
        )
        self.membership = MembershipApplication.objects.create(
            user=self.user,
            middle_name='Q',
            gender='female',
            civil_status='single',
            education='college',
            sitio='Sitio 1',
            barangay='Barangay 1',
            city='Leganes',
            province='Iloilo',
            ownership_type='owned',
            farm_location='Farm 1',
            bufia_farm_location='BUFIA Area',
            farm_size=Decimal('1.50'),
            payment_method='online',
            payment_status='pending',
        )
        self.client.force_login(self.user)

    @patch('bufia.views.payment_views.paymongo_create_checkout_session')
    def test_create_membership_payment_redirects_to_paymongo_checkout(self, mock_create_checkout):
        mock_create_checkout.return_value = {
            'id': 'cs_paymongo_membership_1',
            'attributes': {
                'checkout_url': 'https://checkout.paymongo.test/session-1',
            },
        }

        response = self.client.get(reverse('create_membership_payment', args=[self.membership.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://checkout.paymongo.test/session-1')

        payment = Payment.objects.get(
            content_type=ContentType.objects.get_for_model(MembershipApplication),
            object_id=self.membership.pk,
        )
        self.assertEqual(payment.payment_provider, 'paymongo')
        self.assertEqual(payment.stripe_session_id, 'cs_paymongo_membership_1')
        self.assertEqual(payment.status, 'pending')

        kwargs = mock_create_checkout.call_args.kwargs
        self.assertEqual(kwargs['payment_method_types'], ['gcash'])
        self.assertEqual(kwargs['metadata']['membership_id'], str(self.membership.pk))

    @patch('bufia.views.payment_views.paymongo_retrieve_checkout_session')
    def test_payment_success_marks_membership_paid_with_paymongo(self, mock_retrieve_checkout):
        payment = Payment.objects.create(
            user=self.user,
            payment_type='membership',
            amount=Decimal('500.00'),
            currency='PHP',
            status='pending',
            payment_provider='paymongo',
            stripe_session_id='cs_paymongo_membership_2',
            content_type=ContentType.objects.get_for_model(MembershipApplication),
            object_id=self.membership.pk,
        )
        mock_retrieve_checkout.return_value = {
            'type': 'checkout_session',
            'id': 'cs_paymongo_membership_2',
            'attributes': {
                'payment_intent': {
                    'id': 'pi_paymongo_membership_2',
                    'attributes': {
                        'status': 'succeeded',
                        'payments': [
                            {
                                'id': 'pay_paymongo_membership_2',
                                'attributes': {
                                    'status': 'paid',
                                    'amount': 50000,
                                },
                            }
                        ],
                    },
                },
            },
        }

        response = self.client.get(
            reverse('payment_success'),
            {
                'type': 'membership',
                'id': self.membership.pk,
                'transaction_id': payment.internal_transaction_id,
            },
        )

        self.assertRedirects(response, reverse('membership_slip'), fetch_redirect_response=False)
        self.membership.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(self.membership.payment_status, 'paid')
        self.assertEqual(self.membership.payment_method, 'online')
        self.assertEqual(payment.payment_provider, 'paymongo')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_paymongo_membership_2')
        self.assertEqual(payment.stripe_charge_id, 'pay_paymongo_membership_2')

    def test_paymongo_webhook_marks_membership_paid(self):
        payment = Payment.objects.create(
            user=self.user,
            payment_type='membership',
            amount=Decimal('500.00'),
            currency='PHP',
            status='pending',
            payment_provider='paymongo',
            stripe_session_id='cs_paymongo_membership_3',
            content_type=ContentType.objects.get_for_model(MembershipApplication),
            object_id=self.membership.pk,
        )

        payload = {
            'data': {
                'attributes': {
                    'type': 'checkout_session.payment.paid',
                    'data': {
                        'id': 'cs_paymongo_membership_3',
                        'type': 'checkout_session',
                        'attributes': {
                            'metadata': {
                                'type': 'membership',
                                'item_id': str(self.membership.pk),
                                'membership_id': str(self.membership.pk),
                                'user_id': str(self.user.pk),
                                'internal_transaction_id': payment.internal_transaction_id,
                            },
                            'payment_intent': {
                                'id': 'pi_paymongo_membership_3',
                                'attributes': {
                                    'status': 'succeeded',
                                    'payments': [
                                        {
                                            'id': 'pay_paymongo_membership_3',
                                            'attributes': {
                                                'status': 'paid',
                                                'amount': 50000,
                                            },
                                        }
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }
        payload_bytes = json.dumps(payload).encode('utf-8')
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b'whsk_test_secret',
            f'{timestamp}.{payload_bytes.decode("utf-8")}'.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            reverse('paymongo_webhook'),
            data=payload_bytes,
            content_type='application/json',
            HTTP_PAYMONGO_SIGNATURE=f't={timestamp},te={signature}',
        )

        self.assertEqual(response.status_code, 200)
        self.membership.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(self.membership.payment_status, 'paid')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.payment_provider, 'paymongo')
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_paymongo_membership_3')
        self.assertEqual(payment.stripe_charge_id, 'pay_paymongo_membership_3')
