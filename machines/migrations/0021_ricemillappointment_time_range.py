from decimal import Decimal
from datetime import time

from django.db import migrations, models


def backfill_appointment_time_range(apps, schema_editor):
    RiceMillAppointment = apps.get_model('machines', 'RiceMillAppointment')

    mapping = {
        'morning': (time(8, 0), time(12, 0)),
        'afternoon': (time(13, 0), time(17, 0)),
        '08:00-09:00': (time(8, 0), time(9, 0)),
        '09:00-10:00': (time(9, 0), time(10, 0)),
        '10:00-11:00': (time(10, 0), time(11, 0)),
        '11:00-12:00': (time(11, 0), time(12, 0)),
        '13:00-14:00': (time(13, 0), time(14, 0)),
        '14:00-15:00': (time(14, 0), time(15, 0)),
        '15:00-16:00': (time(15, 0), time(16, 0)),
        '16:00-17:00': (time(16, 0), time(17, 0)),
    }

    for appointment in RiceMillAppointment.objects.all():
        start_time = appointment.start_time
        end_time = appointment.end_time
        if not start_time or not end_time:
            if appointment.time_slot in mapping:
                start_time, end_time = mapping[appointment.time_slot]
            elif appointment.time_slot and '-' in appointment.time_slot:
                try:
                    start_raw, end_raw = appointment.time_slot.split('-', 1)
                    start_time = time.fromisoformat(start_raw)
                    end_time = time.fromisoformat(end_raw)
                except ValueError:
                    start_time = start_time or time(9, 0)
                    end_time = end_time or time(10, 0)
            else:
                start_time = start_time or time(9, 0)
                end_time = end_time or time(10, 0)

        duration_minutes = max(((end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)), 0)
        total_amount = (Decimal(duration_minutes) / Decimal('60') * Decimal('150.00')).quantize(Decimal('0.01'))

        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.time_slot = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        appointment.total_amount = total_amount
        appointment.save(update_fields=['start_time', 'end_time', 'time_slot', 'total_amount'])


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0020_ricemillappointment_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='ricemillappointment',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricemillappointment',
            name='start_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ricemillappointment',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='ricemillappointment',
            name='time_slot',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.RunPython(backfill_appointment_time_range, migrations.RunPython.noop),
    ]
