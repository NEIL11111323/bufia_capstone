# Make sector_number unique after data population

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_populate_sectors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sector',
            name='sector_number',
            field=models.IntegerField(
                choices=[(1, 'Sector 1'), (2, 'Sector 2'), (3, 'Sector 3'), 
                        (4, 'Sector 4'), (5, 'Sector 5'), (6, 'Sector 6'), 
                        (7, 'Sector 7'), (8, 'Sector 8'), (9, 'Sector 9'), 
                        (10, 'Sector 10')],
                help_text='Sector number (1-10)',
                unique=True
            ),
        ),
    ]
