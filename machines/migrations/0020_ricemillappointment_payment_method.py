from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0019_add_payment_fields_manual'),
    ]

    operations = [
        migrations.AddField(
            model_name='ricemillappointment',
            name='payment_method',
            field=models.CharField(
                blank=True,
                choices=[('online', 'Online Payment'), ('face_to_face', 'Face-to-Face Payment')],
                max_length=20,
                null=True,
            ),
        ),
    ]
