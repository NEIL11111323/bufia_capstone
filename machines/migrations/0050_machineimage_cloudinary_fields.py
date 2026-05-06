import machines.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0049_dryerrental_confirmed_quantity_sacks'),
    ]

    operations = [
        migrations.AlterField(
            model_name='machineimage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=machines.models.machine_image_upload_path),
        ),
        migrations.AddField(
            model_name='machineimage',
            name='cloudinary_public_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='machineimage',
            name='cloudinary_url',
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
    ]
