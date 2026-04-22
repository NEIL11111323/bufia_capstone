from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_rename_users_membe_sector__idx_users_membe_sector__fde3ad_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='must_change_password',
            field=models.BooleanField(
                default=False,
                help_text='Require the user to change their password on the next login.',
            ),
        ),
    ]
