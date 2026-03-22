from decimal import Decimal

from django.db import migrations


def recalculate_ricemill_totals(apps, schema_editor):
    RiceMillAppointment = apps.get_model('machines', 'RiceMillAppointment')
    for appointment in RiceMillAppointment.objects.all():
        rice_quantity = appointment.rice_quantity or Decimal('0')
        appointment.total_amount = (rice_quantity * Decimal('3.00')).quantize(Decimal('0.01'))
        appointment.save(update_fields=['total_amount'])


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0021_ricemillappointment_time_range'),
    ]

    operations = [
        migrations.RunPython(recalculate_ricemill_totals, migrations.RunPython.noop),
    ]
