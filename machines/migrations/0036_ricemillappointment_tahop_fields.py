from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0035_remove_maintenance_issue_reported'),
    ]

    operations = [
        migrations.AddField(
            model_name='ricemillappointment',
            name='sell_tahop',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ricemillappointment',
            name='tahop_price_per_kg',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Tahop selling price per kilogram', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ricemillappointment',
            name='tahop_total_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.AddField(
            model_name='ricemillappointment',
            name='tahop_weight',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Tahop weight in kilograms', max_digits=10, null=True),
        ),
    ]
