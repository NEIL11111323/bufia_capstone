from django.db import migrations, models
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_update_must_change_password_help_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='MembershipApplicationProof',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.FileField(help_text='Additional land ownership or tenancy proof document.', upload_to='membership/land_proofs/', validators=[users.models.validate_membership_land_proof])),
                ('display_order', models.PositiveSmallIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='proof_documents', to='users.membershipapplication')),
            ],
            options={
                'verbose_name': 'Membership Application Proof',
                'verbose_name_plural': 'Membership Application Proofs',
                'ordering': ['display_order', 'id'],
            },
        ),
    ]
