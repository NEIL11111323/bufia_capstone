from django.db import migrations, models


def backfill_member_last_viewed_at(apps, schema_editor):
    RentalPackage = apps.get_model('machines', 'RentalPackage')
    for package in RentalPackage.objects.all().only('id', 'updated_at'):
        RentalPackage.objects.filter(
            pk=package.pk,
            member_last_viewed_at__isnull=True,
        ).update(member_last_viewed_at=package.updated_at)


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0046_add_diesel_consumption'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalpackage',
            name='member_last_viewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_member_last_viewed_at, migrations.RunPython.noop),
    ]
