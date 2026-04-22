from django.db import migrations, models


def set_bufia_rice_share_source(apps, schema_editor):
    RiceMillAppointment = apps.get_model('machines', 'RiceMillAppointment')
    RiceSaleSetting = apps.get_model('reports', 'RiceSaleSetting')

    settings_obj = RiceSaleSetting.objects.filter(pk=1).first()
    if not settings_obj or not settings_obj.harvest_milling_user_id:
        return

    RiceMillAppointment.objects.filter(
        user_id=settings_obj.harvest_milling_user_id
    ).update(booking_source='bufia_rice_share')


def reset_booking_source(apps, schema_editor):
    RiceMillAppointment = apps.get_model('machines', 'RiceMillAppointment')
    RiceMillAppointment.objects.filter(
        booking_source='bufia_rice_share'
    ).update(booking_source='member')


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_ricesalesetting_harvest_milling_user'),
        ('machines', '0037_machine_asset_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='ricemillappointment',
            name='booking_source',
            field=models.CharField(
                choices=[('member', 'Member Rice'), ('bufia_rice_share', 'BUFIA Rice Share')],
                default='member',
                max_length=30,
            ),
        ),
        migrations.RunPython(set_bufia_rice_share_source, reset_booking_source),
    ]
