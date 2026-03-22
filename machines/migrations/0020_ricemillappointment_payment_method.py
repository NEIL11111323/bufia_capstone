from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0018_rental_amount_paid_rental_or_number_and_more'),
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
