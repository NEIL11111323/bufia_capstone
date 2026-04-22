from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0033_dryerrental_batch_grouping'),
    ]

    operations = [
        migrations.AddField(
            model_name='dryerrental',
            name='actual_drying_hours',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
