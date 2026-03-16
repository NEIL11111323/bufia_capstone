# Generated migration for notification enhancements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_usernotification_action_url_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotification',
            name='priority',
            field=models.CharField(
                choices=[
                    ('critical', 'Critical'),
                    ('important', 'Important'),
                    ('normal', 'Normal'),
                    ('low', 'Low')
                ],
                default='normal',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='usernotification',
            name='category',
            field=models.CharField(
                choices=[
                    ('rental', 'Rental'),
                    ('operator', 'Operator'),
                    ('payment', 'Payment'),
                    ('maintenance', 'Maintenance'),
                    ('system', 'System'),
                    ('irrigation', 'Irrigation'),
                    ('appointment', 'Appointment'),
                    ('membership', 'Membership')
                ],
                default='system',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='usernotification',
            name='title',
            field=models.CharField(blank=True, help_text='Short notification title', max_length=200),
        ),
    ]
