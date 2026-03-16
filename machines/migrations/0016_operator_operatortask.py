# Generated migration for Operator and OperatorTask models

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('machines', '0015_rename_machines_ha_rental_idx_machines_ha_rental__6891a0_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Operator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operator_id', models.CharField(help_text='Custom operator ID (e.g., OP-001)', max_length=20, unique=True)),
                ('contact_number', models.CharField(max_length=15, validators=[django.core.validators.RegexValidator(message='Enter a valid phone number', regex='^\\+?1?\\d{9,15}$')])),
                ('address', models.TextField()),
                ('status', models.CharField(choices=[('available', 'Available'), ('busy', 'Busy'), ('inactive', 'Inactive')], default='available', max_length=20)),
                ('hire_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('current_machine', models.ForeignKey(blank=True, help_text='Currently assigned machine', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='current_operator', to='machines.machine')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='operator_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['operator_id'],
            },
        ),
        migrations.CreateModel(
            name='OperatorTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_type', models.CharField(choices=[('rental', 'Equipment Rental'), ('rice_mill', 'Rice Milling'), ('irrigation', 'Irrigation')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('scheduled_date', models.DateField()),
                ('completion_date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operator_tasks', to='machines.machine')),
                ('member', models.ForeignKey(help_text='Farmer requesting service', on_delete=django.db.models.deletion.CASCADE, related_name='requested_tasks', to=settings.AUTH_USER_MODEL)),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='machines.operator')),
                ('rental', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='operator_tasks', to='machines.rental')),
            ],
            options={
                'ordering': ['-scheduled_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='operator',
            index=models.Index(fields=['operator_id'], name='machines_op_operato_idx'),
        ),
        migrations.AddIndex(
            model_name='operator',
            index=models.Index(fields=['status'], name='machines_op_status_idx'),
        ),
        migrations.AddIndex(
            model_name='operatortask',
            index=models.Index(fields=['operator', 'status'], name='machines_op_operato_status_idx'),
        ),
        migrations.AddIndex(
            model_name='operatortask',
            index=models.Index(fields=['scheduled_date'], name='machines_op_schedul_idx'),
        ),
    ]
