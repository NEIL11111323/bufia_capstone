from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0039_rental_actual_pickup_at_rental_actual_return_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental',
            name='cancel_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='cancellation_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Not Cancelled'),
                    ('customer', 'Cancelled by Customer'),
                    ('admin', 'Cancelled by Admin'),
                    ('auto_conflict', 'Auto Cancelled Due to Conflict'),
                ],
                default='',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='follow_up_action',
            field=models.CharField(
                choices=[
                    ('none', 'No Follow-up Requested'),
                    ('refund_requested', 'Refund Requested'),
                    ('reschedule_requested', 'Reschedule Requested'),
                    ('refund_processed', 'Refund Processed'),
                    ('rescheduled', 'Rescheduled'),
                ],
                default='none',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='follow_up_admin_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='follow_up_requested_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='follow_up_resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='system_note',
            field=models.TextField(blank=True),
        ),
    ]
