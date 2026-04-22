from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0028_alter_dryerrental_machine_alter_machine_machine_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='dryerrental',
            name='estimated_drying_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Estimated number of sun-drying days required for solar dryers.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='dryerrental',
            name='solar_drying_notes',
            field=models.TextField(
                blank=True,
                help_text='Required setup notes for solar dryers, such as expected sun exposure or drying arrangement.',
            ),
        ),
    ]
