from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RiceSaleSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_price_per_sack', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('is_available_for_sale', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_rice_sale_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Rice Sale Setting',
                'verbose_name_plural': 'Rice Sale Settings',
            },
        ),
        migrations.CreateModel(
            name='RiceSale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sacks', models.DecimalField(decimal_places=2, max_digits=10)),
                ('price_per_sack', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('reference_number', models.CharField(blank=True, max_length=30, unique=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rice_purchases', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Rice Sale',
                'verbose_name_plural': 'Rice Sales',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
