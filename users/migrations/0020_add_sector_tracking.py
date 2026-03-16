# Generated migration for sector tracking enhancement

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_customuser_role'),
    ]

    operations = [
        # Enhance Sector model
        migrations.AddField(
            model_name='sector',
            name='sector_number',
            field=models.IntegerField(
                choices=[(1, 'Sector 1'), (2, 'Sector 2'), (3, 'Sector 3'), 
                        (4, 'Sector 4'), (5, 'Sector 5'), (6, 'Sector 6'), 
                        (7, 'Sector 7'), (8, 'Sector 8'), (9, 'Sector 9'), 
                        (10, 'Sector 10')],
                help_text='Sector number (1-10)',
                null=True,
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='sector',
            name='area_coverage',
            field=models.TextField(
                blank=True,
                help_text='Geographic boundaries and coverage area'
            ),
        ),
        migrations.AddField(
            model_name='sector',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Whether this sector is currently active'
            ),
        ),
        migrations.AlterField(
            model_name='sector',
            name='name',
            field=models.CharField(
                help_text="Area name (e.g., 'North District')",
                max_length=100
            ),
        ),
        migrations.AlterField(
            model_name='sector',
            name='description',
            field=models.TextField(
                blank=True,
                help_text='Detailed description of the sector'
            ),
        ),
        
        # Enhance MembershipApplication model
        migrations.AddField(
            model_name='membershipapplication',
            name='sector_confirmed',
            field=models.BooleanField(
                default=False,
                help_text='User confirmed sector selection'
            ),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='sector_change_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason for sector change by admin'
            ),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='previous_sector',
            field=models.ForeignKey(
                blank=True,
                help_text='Previous sector before reassignment',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='previous_members',
                to='users.sector'
            ),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='sector_changed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp of last sector change',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='sector_changed_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Admin who changed the sector',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sector_changes_made',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name='membershipapplication',
            name='sector',
            field=models.ForeignKey(
                blank=True,
                help_text='Sector selected by user during application',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='users.sector'
            ),
        ),
        
        # Add indexes
        migrations.AlterModelOptions(
            name='sector',
            options={
                'ordering': ['sector_number'],
                'verbose_name': 'Sector',
                'verbose_name_plural': 'Sectors'
            },
        ),
        migrations.AddIndex(
            model_name='sector',
            index=models.Index(fields=['sector_number'], name='users_secto_sector__idx'),
        ),
        migrations.AddIndex(
            model_name='sector',
            index=models.Index(fields=['is_active'], name='users_secto_is_acti_idx'),
        ),
        migrations.AddIndex(
            model_name='membershipapplication',
            index=models.Index(
                fields=['sector', 'is_approved'],
                name='users_membe_sector__idx'
            ),
        ),
        migrations.AddIndex(
            model_name='membershipapplication',
            index=models.Index(
                fields=['assigned_sector', 'is_approved'],
                name='users_membe_assigne_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='membershipapplication',
            index=models.Index(
                fields=['payment_status'],
                name='users_membe_payment_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='membershipapplication',
            index=models.Index(
                fields=['submission_date'],
                name='users_membe_submiss_idx'
            ),
        ),
    ]
