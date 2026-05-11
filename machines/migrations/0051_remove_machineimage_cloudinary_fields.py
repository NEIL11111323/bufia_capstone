import machines.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0050_machineimage_cloudinary_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='machineimage',
            name='cloudinary_public_id',
        ),
        migrations.RemoveField(
            model_name='machineimage',
            name='cloudinary_url',
        ),
        migrations.AlterField(
            model_name='machineimage',
            name='image',
            field=models.ImageField(upload_to=machines.models.machine_image_upload_path),
        ),
    ]
