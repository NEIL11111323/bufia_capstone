from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import date

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
        return f"Sector {self.sector_number} - {self.name}"
    
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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='membership_application')
    submission_date = models.DateField(default=timezone.now)
    is_current = models.BooleanField(default=True, help_text="Whether this is the current application")
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    
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
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=[
        ('online', 'Online Payment'),
        ('face_to_face', 'Face-to-Face Payment'),
    ], default='face_to_face')
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ], default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Approval information
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
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
    def age(self):
        """Calculate age based on birth_date"""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
