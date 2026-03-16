from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0012_add_actual_completion_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental',
            name='receipt_number',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='machine',
            name='status',
            field=models.CharField(
                choices=[
                    ('available', 'Available'),
                    ('maintenance', 'Under Maintenance'),
                    ('rented', 'In Use'),
                ],
                default='available',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='rental',
            name='settlement_status',
            field=models.CharField(
                choices=[
                    ('to_be_determined', 'TO BE DETERMINED'),
                    ('pending', 'Pending'),
                    ('waiting_for_delivery', 'WAITING FOR DELIVERY'),
                    ('paid', 'PAID'),
                    ('cancelled', 'Cancelled'),
                ],
                default='to_be_determined',
                max_length=30,
            ),
        ),
    ]
