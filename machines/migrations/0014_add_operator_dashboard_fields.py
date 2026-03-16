from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0013_add_receipt_number_and_workflow_choices'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='rental',
            name='assigned_operator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='operator_rentals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='operator_last_update_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='operator_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='operator_reported_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='operator_status',
            field=models.CharField(
                choices=[
                    ('unassigned', 'Unassigned'),
                    ('assigned', 'Assigned'),
                    ('traveling', 'Traveling'),
                    ('operating', 'Operating'),
                    ('completed', 'Work Completed'),
                    ('harvest_reported', 'Harvest Reported'),
                ],
                default='unassigned',
                max_length=30,
            ),
        ),
    ]
