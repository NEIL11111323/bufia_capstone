from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0042_rentalpackage_alter_machine_machine_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='machine',
            name='horsepower',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
