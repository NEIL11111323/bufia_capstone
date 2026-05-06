from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0048_machine_flatbed_max_sack_capacity'),
    ]

    operations = [
        migrations.AddField(
            model_name='dryerrental',
            name='confirmed_quantity_sacks',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
    ]
