from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0032_dryerrental_estimated_end_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dryerrental',
            name='batch_number',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='dryerrental',
            name='batch_total',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='dryerrental',
            name='parent_rental',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_batches', to='machines.dryerrental'),
        ),
    ]
