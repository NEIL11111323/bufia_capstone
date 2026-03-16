# Generated migration for IN-KIND Equipment Rental Workflow

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('machines', '0009_machine_in_kind_farmer_share_and_more'),
    ]

    operations = [
        # Add workflow_state and related fields to Rental model
        migrations.AddField(
            model_name='rental',
            name='workflow_state',
            field=models.CharField(
                choices=[
                    ('requested', 'Requested'),
                    ('pending_approval', 'Pending Approval'),
                    ('approved', 'Approved'),
                    ('in_progress', 'In Progress'),
                    ('harvest_report_submitted', 'Harvest Report Submitted'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='requested',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='actual_handover_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rental',
            name='total_rice_sacks_harvested',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Total sacks harvested by operator',
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='bufia_share',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="BUFIA's share (1 sack per 9 harvested)",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='member_share',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Member's share (remaining sacks)",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='rental',
            name='state_changed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rental_state_changes',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Create HarvestReport model
        migrations.CreateModel(
            name='HarvestReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_rice_sacks_harvested', models.DecimalField(decimal_places=2, help_text='Total sacks harvested by operator', max_digits=10)),
                ('report_timestamp', models.DateTimeField(auto_now_add=True)),
                ('recording_timestamp', models.DateTimeField(auto_now_add=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('verification_notes', models.TextField(blank=True)),
                ('is_rejected', models.BooleanField(default=False)),
                ('rejection_reason', models.TextField(blank=True)),
                ('rejection_timestamp', models.DateTimeField(blank=True, null=True)),
                ('recorded_by_admin', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_harvest_reports', to=settings.AUTH_USER_MODEL)),
                ('rental', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='harvest_reports', to='machines.rental')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_harvest_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Harvest Report',
                'verbose_name_plural': 'Harvest Reports',
                'ordering': ['-report_timestamp'],
            },
        ),
        # Create Settlement model
        migrations.CreateModel(
            name='Settlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('settlement_date', models.DateTimeField(auto_now_add=True)),
                ('bufia_share', models.DecimalField(decimal_places=2, max_digits=10)),
                ('member_share', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_harvested', models.DecimalField(decimal_places=2, max_digits=10)),
                ('settlement_reference', models.CharField(max_length=50, unique=True)),
                ('finalized_at', models.DateTimeField(auto_now_add=True)),
                ('finalized_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finalized_settlements', to=settings.AUTH_USER_MODEL)),
                ('rental', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='machines.rental')),
            ],
            options={
                'verbose_name': 'Settlement',
                'verbose_name_plural': 'Settlements',
                'ordering': ['-finalized_at'],
            },
        ),
        # Create RentalStateChange model
        migrations.CreateModel(
            name='RentalStateChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_state', models.CharField(max_length=30)),
                ('to_state', models.CharField(max_length=30)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('reason', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('changed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rental_state_changes_made', to=settings.AUTH_USER_MODEL)),
                ('rental', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='state_changes', to='machines.rental')),
            ],
            options={
                'verbose_name': 'Rental State Change',
                'verbose_name_plural': 'Rental State Changes',
                'ordering': ['-changed_at'],
            },
        ),
        # Add indexes to HarvestReport
        migrations.AddIndex(
            model_name='harvestreport',
            index=models.Index(fields=['rental', 'is_verified'], name='machines_ha_rental_idx'),
        ),
        migrations.AddIndex(
            model_name='harvestreport',
            index=models.Index(fields=['recorded_by_admin', 'report_timestamp'], name='machines_ha_recorded_idx'),
        ),
        # Add indexes to Settlement
        migrations.AddIndex(
            model_name='settlement',
            index=models.Index(fields=['rental', 'finalized_at'], name='machines_se_rental_idx'),
        ),
        migrations.AddIndex(
            model_name='settlement',
            index=models.Index(fields=['settlement_reference'], name='machines_se_reference_idx'),
        ),
        # Add indexes to RentalStateChange
        migrations.AddIndex(
            model_name='rentalstatechange',
            index=models.Index(fields=['rental', 'changed_at'], name='machines_rs_rental_idx'),
        ),
        migrations.AddIndex(
            model_name='rentalstatechange',
            index=models.Index(fields=['changed_by', 'changed_at'], name='machines_rs_changed_idx'),
        ),
    ]
