# Migration to add actual_completion_time field for early rental completion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0011_add_state_changed_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental',
            name='actual_completion_time',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Actual time when rental was completed (for early completions)'
            ),
        ),
    ]
