from django.db import migrations, models


def populate_machine_categories(apps, schema_editor):
    Machine = apps.get_model('machines', 'Machine')
    mapping = {
        'rice_mill': 'rice_mill',
        'tractor_4wd': 'tractor',
        'hand_tractor': 'tractor',
        'transplanter_walking': 'transplanter',
        'transplanter_riding': 'transplanter',
        'precision_seeder': 'seeder',
        'harvester': 'harvester',
        'thresher': 'thresher',
        'flatbed_dryer': 'dryer',
        'solar_dryer': 'dryer',
        'circulating_dryer': 'dryer',
        'other': 'other',
    }
    for machine in Machine.objects.all():
        machine.machine_category = mapping.get(machine.machine_type, 'other')
        machine.save(update_fields=['machine_category'])


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0043_machine_horsepower'),
    ]

    operations = [
        migrations.AddField(
            model_name='machine',
            name='machine_category',
            field=models.CharField(
                choices=[
                    ('tractor', 'Tractor'),
                    ('transplanter', 'Transplanter'),
                    ('seeder', 'Seeder'),
                    ('harvester', 'Harvester'),
                    ('thresher', 'Thresher'),
                    ('dryer', 'Dryer'),
                    ('rice_mill', 'Rice Mill'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.RunPython(populate_machine_categories, migrations.RunPython.noop),
    ]
