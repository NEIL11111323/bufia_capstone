from django.db import migrations


def create_missing_irrigation_season_tables(apps, schema_editor):
    existing_tables = set(schema_editor.connection.introspection.table_names())

    CroppingSeason = apps.get_model('irrigation', 'CroppingSeason')
    IrrigationSeasonRecord = apps.get_model('irrigation', 'IrrigationSeasonRecord')

    if CroppingSeason._meta.db_table not in existing_tables:
        schema_editor.create_model(CroppingSeason)
        existing_tables.add(CroppingSeason._meta.db_table)

    if IrrigationSeasonRecord._meta.db_table not in existing_tables:
        schema_editor.create_model(IrrigationSeasonRecord)


class Migration(migrations.Migration):

    dependencies = [
        ('irrigation', '0005_croppingseason_irrigationseasonrecord'),
    ]

    operations = [
        migrations.RunPython(create_missing_irrigation_season_tables, migrations.RunPython.noop),
    ]
