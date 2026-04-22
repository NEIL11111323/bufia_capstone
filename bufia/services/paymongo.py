import base64
import base64
import hashlib
import hmac
import json
from decimal import Decimal
from urllib import error, request

from django.conf import settings


class PayMongoAPIError(Exception):
    """Raised when PayMongo returns an API or transport error."""


def is_configured() -> bool:
    secret_key = (getattr(settings, 'PAYMONGO_SECRET_KEY', '') or '').strip()
    public_key = (getattr(settings, 'PAYMONGO_PUBLIC_KEY', '') or '').strip()
    return bool(secret_key and public_key)


def get_enabled_payment_methods():
    raw_value = getattr(settings, 'PAYMONGO_PAYMENT_METHODS', ['gcash']) or ['gcash']
    if isinstance(raw_value, str):
        methods = [item.strip().lower() for item in raw_value.split(',') if item.strip()]
    else:
        methods = [str(item).strip().lower() for item in raw_value if str(item).strip()]
    return methods or ['gcash']


def _authorization_header():
    secret_key = (getattr(settings, 'PAYMONGO_SECRET_KEY', '') or '').strip()
    token = base64.b64encode(f'{secret_key}:'.encode('utf-8')).decode('ascii')
    return f'Basic {token}'


def _api_request(method, endpoint, payload=None):
    headers = {
        'Accept': 'application/json',
        'Authorization': _authorization_header(),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    api_request = request.Request(
        url=f'https://api.paymongo.com{endpoint}',
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with request.urlopen(api_request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(body)
            errors = payload.get('errors') or []
            detail = '; '.join(
                item.get('detail') or item.get('code') or 'Unknown PayMongo error'
                for item in errors
            )
        except Exception:
            detail = body or exc.reason
        raise PayMongoAPIError(detail or 'PayMongo request failed.') from exc
    except error.URLError as exc:
        raise PayMongoAPIError(f'Unable to reach PayMongo: {exc.reason}') from exc


def create_checkout_session(
    *,
    amount_centavos,
    name,
    description,
    success_url,
    cancel_url,
    metadata,
    reference_number,
    customer_email=None,
    customer_name=None,
    payment_method_types=None,
):
    attributes = {
        'description': description,
        'payment_method_types': payment_method_types or get_enabled_payment_methods(),
        'line_items': [
            {
                'amount': int(amount_centavos),
                'currency': 'PHP',
                'name': name,
                'quantity': 1,
                'description': description,
            }
        ],
        'reference_number': reference_number,
        'send_email_receipt': True,
        'show_description': True,
        'show_line_items': True,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'metadata': metadata or {},
    }

    if customer_email or customer_name:
        attributes['billing'] = {
            'name': customer_name or customer_email or 'BUFIA Member',
            'email': customer_email,
        }

    payload = {'data': {'attributes': attributes}}
    return _api_request('POST', '/v1/checkout_sessions', payload)['data']


def retrieve_checkout_session(checkout_session_id):
    return _api_request('GET', f'/v1/checkout_sessions/{checkout_session_id}')['data']


def checkout_session_attributes(session_payload):
    if not session_payload:
        return {}
    if isinstance(session_payload, dict):
        if session_payload.get('type') == 'checkout_session' and isinstance(session_payload.get('attributes'), dict):
            return session_payload.get('attributes', {})
        if isinstance(session_payload.get('data'), dict):
            return session_payload.get('data', {}).get('attributes', {})
        # Compatibility for legacy Stripe-like mocked session payloads used in older tests.
        return session_payload
    return {}


def checkout_session_is_successful(session_payload) -> bool:
    attributes = checkout_session_attributes(session_payload)
    if not attributes:
        return False

    if attributes.get('status') in {'paid', 'completed'}:
        return True
    if (
        attributes.get('status') in {'complete', 'completed', 'paid'}
        and attributes.get('payment_status') in {'paid', 'completed', None}
    ):
        return True

    payment_intent = attributes.get('payment_intent') or {}
    if isinstance(payment_intent, str):
        return attributes.get('payment_status') == 'paid'
    payment_intent_attributes = payment_intent.get('attributes', {})
    if payment_intent_attributes.get('status') in {'paid', 'succeeded'}:
        return True

    for payment in payment_intent_attributes.get('payments') or []:
        if (payment.get('attributes') or {}).get('status') == 'paid':
            return True

    return False


def extract_payment_intent_id(session_payload):
    attributes = checkout_session_attributes(session_payload)
    payment_intent = attributes.get('payment_intent') or {}
    if isinstance(payment_intent, str):
        return payment_intent
    return payment_intent.get('id')


def extract_payment_id(session_payload):
    attributes = checkout_session_attributes(session_payload)
    payment_intent = attributes.get('payment_intent') or {}
    if not isinstance(payment_intent, dict):
        return None
    payment_intent_attributes = payment_intent.get('attributes', {})
    payments = payment_intent_attributes.get('payments') or []
    if not payments:
        return None
    return payments[0].get('id')


def extract_paid_amount(session_payload):
    attributes = checkout_session_attributes(session_payload)
    amount_total = attributes.get('amount_total')
    if amount_total is not None:
        return (Decimal(str(amount_total)) / Decimal('100')).quantize(Decimal('0.01'))

    payment_intent = attributes.get('payment_intent') or {}
    payment_intent_attributes = payment_intent.get('attributes', {}) if isinstance(payment_intent, dict) else {}
    payments = payment_intent_attributes.get('payments') or []
    if payments:
        amount = (payments[0].get('attributes') or {}).get('amount')
        if amount is not None:
            return (Decimal(str(amount)) / Decimal('100')).quantize(Decimal('0.01'))

    for line_item in attributes.get('line_items') or []:
        amount = line_item.get('amount')
        quantity = line_item.get('quantity') or 1
        if amount is not None:
            total = Decimal(str(amount * quantity)) / Decimal('100')
            return total.quantize(Decimal('0.01'))

    return Decimal('0.00')


def verify_webhook_signature(raw_payload, signature_header, webhook_secret):
    if not signature_header or not webhook_secret:
        return False

    components = {}
    for part in signature_header.split(','):
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        components[key.strip()] = value.strip()

    timestamp = components.get('t')
    if not timestamp:
        return False

    signed_payload = f'{timestamp}.{raw_payload.decode("utf-8")}'
    expected = hmac.new(
        webhook_secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    return any(
        hmac.compare_digest(expected, components.get(key, ''))
        for key in ('te', 'li')
        if components.get(key)
    )
