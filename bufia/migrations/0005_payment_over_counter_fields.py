from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bufia', '0004_payment_payment_provider'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='amount_received',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='change_given',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
        migrations.AddField(
            model_name='payment',
            name='processed_by',
            field=models.ForeignKey(blank=True, help_text='Staff user who processed the over-the-counter payment.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_payments', to=settings.AUTH_USER_MODEL),
        ),
    ]
