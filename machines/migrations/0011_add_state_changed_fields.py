# Generated migration for state_changed_at and state_changed_by fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('machines', '0010_add_in_kind_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental',
            name='state_changed_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
