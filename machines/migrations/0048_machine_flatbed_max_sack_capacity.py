from decimal import Decimal

from django.db import migrations, models


def seed_flatbed_capacity(apps, schema_editor):
    Machine = apps.get_model('machines', 'Machine')
    Machine.objects.filter(
        machine_type='flatbed_dryer',
        flatbed_max_sack_capacity__isnull=True,
    ).update(flatbed_max_sack_capacity=Decimal('150.00'))


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0047_rentalpackage_member_last_viewed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='machine',
            name='flatbed_max_sack_capacity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.RunPython(seed_flatbed_capacity, migrations.RunPython.noop),
    ]
