from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_ricesalesetting_harvest_milling_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ricesale',
            name='amount_paid',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='change_given',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='claimed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='order_status',
            field=models.CharField(choices=[('reserved', 'Reserved'), ('ready', 'Ready for Pickup'), ('claimed', 'Claimed'), ('cancelled', 'Cancelled')], default='reserved', max_length=20),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='payment_method',
            field=models.CharField(choices=[('gcash', 'Gcash Payment'), ('otc', 'Over the Counter')], default='otc', max_length=20),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='payment_status',
            field=models.CharField(choices=[('pending', 'Pending Payment'), ('paid', 'Paid')], default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='pickup_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='processed_rice_sales', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='ready_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricesale',
            name='rice_type',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
