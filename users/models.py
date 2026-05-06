import os
from datetime import date
from types import SimpleNamespace

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_membership_land_proof(value):
    if not value:
        return

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    extension = os.path.splitext(value.name or '')[1].lower()
    if extension not in allowed_extensions:
        raise ValidationError('Upload a PDF, JPG, JPEG, or PNG file. Mobile phone photos are allowed if they are clear and readable.')

    size_limit = 5 * 1024 * 1024
    if value.size and value.size > size_limit:
        raise ValidationError('Each uploaded file must be 5 MB or smaller.')


def membership_file_exists(field_file):
    if not field_file or not getattr(field_file, 'name', ''):
        return False

    try:
        return field_file.storage.exists(field_file.name)
    except Exception:
        return False


def membership_file_url(field_file):
    if not membership_file_exists(field_file):
        return ''

    try:
        return field_file.url
    except Exception:
        return ''

class CustomUser(AbstractUser):
    # PRESIDENT = 'president'  # Removed President role
    SUPERUSER = 'superuser'
    REGULAR_USER = 'regular_user'
    WATER_TENDER = 'water_tender'
    OPERATOR = 'operator'
    
    ROLE_CHOICES = [
        # (PRESIDENT, 'President'),  # Removed President role
        (SUPERUSER, 'Superuser'),
        (REGULAR_USER, 'Regular User'),
        (WATER_TENDER, 'Water Tender'),
        (OPERATOR, 'Operator'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=REGULAR_USER,
    )
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    
    # Water Tender specific fields
    managed_sectors = models.ManyToManyField('Sector', blank=True, related_name='water_tenders',
                                          help_text="Sectors managed by this water tender")
    
    # Verification fields
    is_verified = models.BooleanField(default=False, help_text="Whether this user's membership has been verified")
    membership_form_submitted = models.BooleanField(default=False, help_text="Whether the user has submitted membership form")
    membership_form_date = models.DateField(null=True, blank=True, help_text="Date when membership form was submitted")
    membership_approved_date = models.DateField(null=True, blank=True, help_text="Date when membership was approved")
    membership_rejected_reason = models.TextField(blank=True, help_text="Reason for membership rejection if applicable")
    membership_approval_banner_seen = models.BooleanField(
        default=False,
        help_text="Whether the user has dismissed the membership approval congratulations banner."
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="Remind the user to change their password (not enforced)."
    )
    
    def is_president(self):
        # Updated to check superuser status instead
        return self.is_superuser
    
    def has_superuser_role(self):
        return self.role == self.SUPERUSER or super().is_superuser
    
    def is_regular_user(self):
        return self.role == self.REGULAR_USER
        
    def is_water_tender(self):
        return self.role == self.WATER_TENDER
    
    def is_operator(self):
        return self.role == self.OPERATOR
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Sector(models.Model):
    """Represents a sector or area within BUFIA's jurisdiction"""
    sector_number = models.IntegerField(
        unique=True,
        choices=[(i, f'Sector {i}') for i in range(1, 11)],
        help_text="Sector number (1-10)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Area name (e.g., 'North District')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the sector"
    )
    area_coverage = models.TextField(
        blank=True,
        help_text="Geographic boundaries and coverage area"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this sector is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sector_number']
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectors'
        indexes = [
            models.Index(fields=['sector_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_members(self):
        """Total approved members in this sector"""
        return self.assigned_members.filter(is_approved=True).count()
    
    @property
    def active_members(self):
        """Total verified members in this sector"""
        return self.assigned_members.filter(
            is_approved=True,
            user__is_verified=True
        ).count()
    
    @property
    def pending_applications(self):
        """Pending applications for this sector"""
        return self.members.filter(
            is_approved=False,
            is_rejected=False
        ).count()
    
    @property
    def average_farm_size(self):
        """Average farm size in this sector"""
        from django.db.models import Avg
        result = self.assigned_members.filter(
            is_approved=True
        ).aggregate(Avg('farm_size'))
        return result['farm_size__avg'] or 0


class MembershipApplication(models.Model):
    WORKFLOW_SUBMITTED = 'submitted'
    WORKFLOW_READY_FOR_SURVEY = 'ready_for_survey'
    WORKFLOW_SURVEYED = 'surveyed'
    WORKFLOW_FINALIZED = 'finalized'
    WORKFLOW_REJECTED = 'rejected'

    WORKFLOW_STATUS_CHOICES = [
        (WORKFLOW_SUBMITTED, 'Submitted'),
        (WORKFLOW_READY_FOR_SURVEY, 'Ready for Survey'),
        (WORKFLOW_SURVEYED, 'Survey Completed'),
        (WORKFLOW_FINALIZED, 'Final Approved'),
        (WORKFLOW_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='membership_application')
    submission_date = models.DateField(default=timezone.now)
    is_current = models.BooleanField(default=True, help_text="Whether this is the current application")
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    workflow_status = models.CharField(
        max_length=30,
        choices=WORKFLOW_STATUS_CHOICES,
        default=WORKFLOW_SUBMITTED,
        help_text="Current membership workflow stage.",
    )
    
    # Sector information
    sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text="Sector selected by user during application"
    )
    assigned_sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_members',
        help_text="Sector assigned by admin during verification"
    )
    
    # Sector tracking fields
    sector_confirmed = models.BooleanField(
        default=False,
        help_text="User confirmed sector selection"
    )
    sector_change_reason = models.TextField(
        blank=True,
        help_text="Reason for sector change by admin"
    )
    previous_sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_members',
        help_text="Previous sector before reassignment"
    )
    sector_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last sector change"
    )
    sector_changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sector_changes_made',
        help_text="Admin who changed the sector"
    )
    
    # Personal information
    middle_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=200, blank=True, null=True)
    civil_status = models.CharField(max_length=20, choices=[
        ('single', 'Single'),
        ('married', 'Married'),
        ('separated', 'Separated'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], null=True, blank=True)
    education = models.CharField(max_length=100, choices=[
        ('elementary', 'Elementary'),
        ('high_school', 'High School'),
        ('vocational', 'Vocational'),
        ('college', 'College'),
        ('graduate', 'Graduate'),
    ], null=True, blank=True)
    national_id_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="National ID number provided by the applicant."
    )
    rcba_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="BUFIA-issued RSBSA number assigned by admin."
    )
    
    # Address
    sitio = models.CharField(max_length=100, null=True, blank=True)
    barangay = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    
    # Farm information
    is_tiller = models.BooleanField(default=False, help_text="Whether the member is an actual tiller")
    lot_number = models.CharField(max_length=50, blank=True, null=True, help_text="Lot number of the farm")
    ownership_type = models.CharField(max_length=50, choices=[
        ('owned', 'Owned'),
        ('leased', 'Leased'),
        ('tenant', 'Tenant'),
        ('shared', 'Shared'),
    ], null=True, blank=True)
    land_owner = models.CharField(max_length=100, blank=True, help_text="Name of land owner if not owned")
    farm_manager = models.CharField(max_length=100, blank=True, help_text="Name of farm manager if not self")
    farm_location = models.CharField(max_length=200, null=True, blank=True)
    bufia_farm_location = models.CharField(max_length=200, null=True, blank=True, 
                                          help_text="Specific location of the farm within BUFIA's jurisdiction")
    farm_size = models.DecimalField(max_digits=8, decimal_places=2, help_text="Size in hectares", null=True, blank=True)
    land_proof_document = models.FileField(
        upload_to='membership/land_proofs/',
        null=True,
        blank=True,
        validators=[validate_membership_land_proof],
        help_text='Clear photo or file showing land ownership or tenancy proof.',
    )
    valid_id_document = models.FileField(
        upload_to='membership/valid_ids/',
        null=True,
        blank=True,
        validators=[validate_membership_land_proof],
        help_text='Clear photo or scanned copy of a valid ID.',
    )
    land_proof_notes = models.TextField(
        blank=True,
        help_text='Optional notes from the applicant about the uploaded land proof.',
    )
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=[
        ('online', 'Gcash Payment'),
        ('face_to_face', 'Over the Counter'),
    ], default='face_to_face')
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ], default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Admin notes visible to the member after approval
    admin_notes = models.TextField(
        blank=True,
        help_text="Notes from admin visible to the member after membership is approved."
    )

    # Approval information
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    survey_ready_date = models.DateField(null=True, blank=True)
    surveyed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='surveyed_membership_applications',
    )
    survey_date = models.DateField(null=True, blank=True)
    surveyed_farm_size = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    survey_notes = models.TextField(blank=True)
    finalized_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finalized_membership_applications',
    )
    finalized_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Membership Application'
        verbose_name_plural = 'Membership Applications'
        indexes = [
            models.Index(fields=['sector', 'is_approved']),
            models.Index(fields=['assigned_sector', 'is_approved']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['submission_date']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {'Approved' if self.is_approved else 'Pending'}"

    @property
    def current_farm_size(self):
        return self.surveyed_farm_size if self.surveyed_farm_size is not None else self.farm_size

    @property
    def workflow_status_label(self):
        return self.get_workflow_status_display()

    @property
    def workflow_status_message(self):
        if self.workflow_status == self.WORKFLOW_FINALIZED:
            return 'Membership is fully approved after review and survey confirmation.'
        if self.workflow_status == self.WORKFLOW_SURVEYED:
            return 'Land survey is complete and waiting for final BUFIA approval.'
        if self.workflow_status == self.WORKFLOW_READY_FOR_SURVEY:
            return 'Admin review is done. This application is ready for land survey scheduling.'
        if self.workflow_status == self.WORKFLOW_REJECTED:
            return self.rejection_reason or 'This application was rejected during membership review.'
        return 'Application submitted and waiting for BUFIA admin review.'

    def get_transaction_id(self):
        """Return the payment transaction ID when available, otherwise a stable fallback."""
        try:
            from django.contrib.contenttypes.models import ContentType
            from bufia.models import Payment

            payment = Payment.objects.filter(
                content_type=ContentType.objects.get_for_model(self.__class__),
                object_id=self.pk,
            ).first()
            if payment and payment.internal_transaction_id:
                return payment.internal_transaction_id
        except Exception:
            pass

        if self.pk:
            return f'BUFIA-MEM-{self.pk:05d}'
        return None

    @property
    def primary_land_proof(self):
        first_related_proof = self.proof_documents.order_by('display_order', 'id').first()
        if first_related_proof:
            return first_related_proof
        if self.land_proof_document:
            return SimpleNamespace(
                document=self.land_proof_document,
                filename=os.path.basename(self.land_proof_document.name),
                is_image=os.path.splitext(self.land_proof_document.name)[1].lower() in {'.jpg', '.jpeg', '.png', '.webp'},
                file_exists=membership_file_exists(self.land_proof_document),
                safe_url=membership_file_url(self.land_proof_document),
                uploaded_at=None,
            )
        return None

    @property
    def land_proofs(self):
        proofs = list(self.proof_documents.order_by('display_order', 'id'))
        if proofs:
            return proofs
        primary = self.primary_land_proof
        return [primary] if primary else []

    @property
    def available_land_proofs(self):
        return [
            proof for proof in self.land_proofs
            if getattr(proof, 'file_exists', False) and getattr(proof, 'safe_url', '')
        ]

    @property
    def available_land_proof_count(self):
        return len(self.available_land_proofs)

    @property
    def missing_land_proofs(self):
        return [
            proof for proof in self.land_proofs
            if not getattr(proof, 'file_exists', False)
        ]

    @property
    def missing_land_proof_count(self):
        return len(self.missing_land_proofs)

    @property
    def has_missing_land_proof_files(self):
        return self.land_proof_count > 0 and self.available_land_proof_count < self.land_proof_count

    @property
    def land_proof_count(self):
        return len(self.land_proofs)

    @property
    def uploadable_land_proof_slots(self):
        return max(0, 2 - self.available_land_proof_count)

    @property
    def can_upload_more_land_proofs(self):
        return self.uploadable_land_proof_slots > 0

    @property
    def land_proof_filename(self):
        primary_proof = self.primary_land_proof
        if not primary_proof:
            return ''
        return primary_proof.filename

    @property
    def land_proof_is_image(self):
        primary_proof = self.primary_land_proof
        if not primary_proof:
            return False
        return primary_proof.is_image

    @property
    def valid_id_filename(self):
        if not self.valid_id_document:
            return ''
        return os.path.basename(self.valid_id_document.name or '')

    @property
    def valid_id_exists(self):
        return membership_file_exists(self.valid_id_document)

    @property
    def valid_id_url(self):
        return membership_file_url(self.valid_id_document)

    @property
    def valid_id_is_image(self):
        if not self.valid_id_document:
            return False
        return os.path.splitext(self.valid_id_document.name or '')[1].lower() in {'.jpg', '.jpeg', '.png'}
    
    @property
    def age(self):
        """Calculate age based on birth_date"""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))


class MembershipApplicationProof(models.Model):
    application = models.ForeignKey(
        MembershipApplication,
        on_delete=models.CASCADE,
        related_name='proof_documents',
    )
    document = models.FileField(
        upload_to='membership/land_proofs/',
        validators=[validate_membership_land_proof],
        help_text='Additional land ownership or tenancy proof document.',
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = 'Membership Application Proof'
        verbose_name_plural = 'Membership Application Proofs'

    def __str__(self):
        return f'Proof {self.display_order + 1} for application #{self.application_id}'

    @property
    def filename(self):
        return os.path.basename(self.document.name or '')

    @property
    def is_image(self):
        return os.path.splitext(self.document.name or '')[1].lower() in {'.jpg', '.jpeg', '.png', '.webp'}

    @property
    def file_exists(self):
        return membership_file_exists(self.document)

    @property
    def safe_url(self):
        return membership_file_url(self.document)


class ActivityLog(models.Model):
    TYPE_REGISTER = 'register'
    TYPE_SUBMIT = 'submit'
    TYPE_APPROVE = 'approve'
    TYPE_REJECT = 'reject'
    TYPE_PAYMENT = 'payment'
    TYPE_SCHEDULE = 'schedule'
    TYPE_MACHINE = 'machine'
    TYPE_BILLING = 'billing'
    TYPE_UPDATE = 'update'
    TYPE_OTHER = 'other'

    TYPE_CHOICES = [
        (TYPE_REGISTER, 'Register'),
        (TYPE_SUBMIT, 'Submit'),
        (TYPE_APPROVE, 'Approve'),
        (TYPE_REJECT, 'Reject'),
        (TYPE_PAYMENT, 'Payment'),
        (TYPE_SCHEDULE, 'Schedule'),
        (TYPE_MACHINE, 'Machine'),
        (TYPE_BILLING, 'Billing'),
        (TYPE_UPDATE, 'Update'),
        (TYPE_OTHER, 'Other'),
    ]

    VISIBILITY_ADMIN = 'admin'
    VISIBILITY_USER = 'user'
    VISIBILITY_BOTH = 'both'

    VISIBILITY_CHOICES = [
        (VISIBILITY_ADMIN, 'Admin Only'),
        (VISIBILITY_USER, 'User Only'),
        (VISIBILITY_BOTH, 'Admin and User'),
    ]

    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_actions',
    )
    subject_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_feed_entries',
    )
    activity_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_OTHER,
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_BOTH,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    related_model = models.CharField(max_length=100, blank=True)
    related_object_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['activity_type', 'created_at']),
            models.Index(fields=['visibility', 'created_at']),
            models.Index(fields=['subject_user', 'created_at']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['related_model', 'related_object_id']),
        ]
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return self.title
