# Generated migration to remove issue_reported field from Maintenance model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0034_dryerrental_actual_drying_hours'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='maintenance',
            name='issue_reported',
        ),
    ]
