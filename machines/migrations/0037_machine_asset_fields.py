from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0036_ricemillappointment_tahop_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='machine',
            name='acquisition_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='machine',
            name='acquisition_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='machine',
            name='brand_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='machine',
            name='model_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='machine',
            name='model_year',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
