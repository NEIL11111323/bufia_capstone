from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_ricesalesetting_ricesale'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ricesalesetting',
            name='harvest_milling_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='harvest_milling_rice_sale_settings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
