from django.db import migrations, models


def mark_existing_stripe_payments(apps, schema_editor):
    Payment = apps.get_model('bufia', 'Payment')
    Payment.objects.filter(
        payment_provider__isnull=True,
    ).exclude(
        stripe_session_id__isnull=True,
        stripe_payment_intent_id__isnull=True,
        stripe_charge_id__isnull=True,
    ).update(payment_provider='stripe')


class Migration(migrations.Migration):

    dependencies = [
        ('bufia', '0003_alter_payment_payment_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_provider',
            field=models.CharField(blank=True, choices=[('stripe', 'Stripe'), ('paymongo', 'PayMongo'), ('manual', 'Manual')], help_text='Payment gateway or channel used for this payment record.', max_length=20, null=True),
        ),
        migrations.RunPython(mark_existing_stripe_payments, migrations.RunPython.noop),
    ]
