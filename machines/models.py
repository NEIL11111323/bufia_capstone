from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import math
import os
from django.utils.text import slugify
import random

def machine_image_path(instance, filename):
    """Generate file path for a machine image"""
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a slug from the machine name
    slug = slugify(instance.name)
    # Return the file path
    return os.path.join('machines/images', f"{slug}_{instance.id}.{ext}")

def rental_payment_slip_path(instance, filename):
    """Generate file path for rental payment slip"""
    # Get the file extension
    ext = filename.split('.')[-1].lower()
    # Generate timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    # Create filename: proof_rental{id}_{timestamp}.{ext}
    new_filename = f"proof_rental{instance.id}_{timestamp}.{ext}"
    # Return the file path organized by year/month
    year_month = timezone.now().strftime('%Y/%m')
    return os.path.join('payment_slips', 'rentals', year_month, new_filename)

def machine_image_upload_path(instance, filename):
    """Generate file path for a MachineImage instance"""
    # Get the file extension
    ext = filename.split('.')[-1]
    
    # Ensure we have a valid machine instance
    if not instance.machine_id:
        # If there's no machine associated yet, use a temporary path
        return os.path.join('machines', 'images', 'temp', f"temp_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}")
    
    # Generate a slug from the machine name
    machine_slug = slugify(instance.machine.name)
    
    # Generate a unique filename
    unique_id = timezone.now().strftime('%Y%m%d%H%M%S')
    
    # Create the directory structure
    directory = os.path.join('machines', 'images', machine_slug)
    
    # Ensure the directory exists
    full_dir_path = os.path.join(settings.MEDIA_ROOT, directory)
    os.makedirs(full_dir_path, exist_ok=True)
    
    # Create a filename with the machine slug, image ID if it exists, and timestamp
    filename = f"{machine_slug}_{unique_id}"
    if instance.pk:
        filename = f"{machine_slug}_{instance.pk}_{unique_id}"
    
    # Return the file path
    return os.path.join(directory, f"{filename}.{ext}")

class Machine(models.Model):
    name = models.CharField(max_length=100)
    machine_type = models.CharField(
        max_length=20,
        choices=[
            ('rice_mill', 'Rice Mill'),
            ('tractor_4wd', '4-Wheel Drive Tractor'),
            ('hand_tractor', 'Hand Tractor'),
            ('transplanter_walking', 'Walk-behind Transplanter'),
            ('transplanter_riding', 'Riding Type Transplanter'),
            ('precision_seeder', 'Precision Seeder'),
            ('harvester', 'Harvester'),
            ('flatbed_dryer', 'Flatbed Dryer'),
            ('other', 'Other'),
        ],
        default='other'
    )
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('maintenance', 'Under Maintenance'),
            ('rented', 'Currently Rented'),
        ],
        default='available'
    )
    rental_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_price = models.CharField(max_length=100, help_text="Enter price (e.g., '1500', '₱3500/hectare', '1/9 sack')")
    stripe_payment_link = models.URLField(max_length=500, blank=True, null=True, help_text="Stripe payment link for online payments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=machine_image_path, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_rent_machine", "Can rent a machine"),
            ("can_schedule_rent", "Can schedule a machine rental"),
        ]
    
    def __str__(self):
        return self.name
    
    def is_available(self):
        return self.status == 'available'
    
    def is_rice_mill(self):
        return self.machine_type == 'rice_mill'
    
    def get_pricing_info(self):
        """Return pricing information based on machine type"""
        if self.machine_type == 'rice_mill' or self.name == 'Flatbed dryer' or self.machine_type == 'flatbed_dryer':
            return {'rate': 150, 'unit': 'hour'}
        elif self.machine_type == 'tractor_4wd' or self.name == '4wheel Drive Tractor':
            return {'rate': 4000, 'unit': 'hectare'}
        elif self.machine_type == 'hand_tractor' or self.name == 'Hand tractor':
            return {'rate': 1000, 'unit': 'flat'}
        elif self.machine_type in ['transplanter_walking', 'transplanter_riding', 'precision_seeder'] or \
             self.name in ['Walk-behind transplanter', 'Riding Type transplanter', 'Precision Seeder']:
            return {'rate': 3500, 'unit': 'hectare'}
        elif self.machine_type == 'harvester' or self.name == 'Harvester':
            return {'rate': '1/9', 'unit': 'sack'}
        else:
            return {'rate': self.current_price, 'unit': 'day'}
    
    def calculate_rental_cost(self, area=1, days=1, yield_amount=0):
        """Calculate rental cost based on machine type and parameters"""
        pricing = self.get_pricing_info()
        
        if pricing['unit'] == 'hour':
            # For hourly pricing (assuming 5 hours per hectare for now)
            hours = max(1, round(area * 5))
            return pricing['rate'] * hours
        elif pricing['unit'] == 'hectare':
            # For per hectare pricing
            return pricing['rate'] * area
        elif pricing['unit'] == 'flat':
            # For flat fee pricing
            return pricing['rate']
        elif pricing['unit'] == 'sack':
            # For harvester, return the number of sacks that will be taken as payment
            if yield_amount <= 0:
                return "N/A - Need yield estimate"
            return math.ceil(yield_amount / 9)
        else:
            # Default daily rate
            return pricing['rate'] * days
    
    def save(self, *args, **kwargs):
        if not self.rental_fee_per_day and self.current_price:
            self.rental_fee_per_day = self.current_price
        super().save(*args, **kwargs)
    
    def get_display_image_url(self):
        """Return the URL of the primary image or the first available image"""
        # First, check if there's a primary image
        primary_images = self.images.filter(is_primary=True)
        if primary_images.exists():
            return primary_images.first().image.url
        
        # If no primary image, check if there are any other images
        if self.images.exists():
            return self.images.first().image.url
        
        # Finally, check if there's a direct image
        if self.image:
            return self.image.url
        
        # If no images are available, return None
        return None

class MachineImage(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=machine_image_upload_path)
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"Image for {self.machine.name}"
    
    def save(self, *args, **kwargs):
        # Debug output
        print(f"Saving MachineImage: machine={self.machine_id}, is_primary={self.is_primary}")
        
        # Check if image file exists
        if self.image:
            print(f"Image file: {self.image.name}")
        else:
            print("No image file")
        
        # Check if this is the first image for the machine
        if not self.pk and not self.machine.images.exists():
            self.is_primary = True
            print("Setting as primary (first image)")
        
        # If this image is set as primary, unset other primary images
        if self.is_primary:
            try:
                MachineImage.objects.filter(
                    machine=self.machine, 
                    is_primary=True
                ).exclude(
                    pk=self.pk
                ).update(
                    is_primary=False
                )
                print("Updated other images to non-primary")
            except Exception as e:
                print(f"Error updating other images: {e}")
        
        # Call the original save method
        try:
            super().save(*args, **kwargs)
            print(f"MachineImage saved successfully, ID: {self.pk}")
        except Exception as e:
            print(f"Error saving MachineImage: {e}")
            raise

class Rental(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='rentals')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rentals')
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Payment fields
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[('online', 'Online Payment'), ('face_to_face', 'Face-to-Face')],
        null=True,
        blank=True
    )
    payment_slip = models.FileField(upload_to=rental_payment_slip_path, null=True, blank=True)
    payment_verified = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_rentals'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Rental')
        verbose_name_plural = _('Rentals')
        permissions = [
            ("can_view_all_rentals", "Can view all rental records"),
            ("can_approve_rentals", "Can approve rental requests"),
        ]
        indexes = [
            # Composite index for fast availability checks
            models.Index(fields=['machine', 'start_date', 'end_date', 'status'], name='rental_availability_idx'),
            # Index for date range queries
            models.Index(fields=['start_date', 'end_date'], name='rental_dates_idx'),
            # Index for user queries
            models.Index(fields=['user', 'status'], name='rental_user_status_idx'),
        ]
        constraints = [
            # Ensure end_date is always >= start_date
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')),
                name='end_date_after_start_date'
            ),
        ]
    
    def __str__(self):
        return f"{self.machine.name} - {self.user.get_full_name()} ({self.start_date} to {self.end_date})"
    
    def get_duration_days(self):
        """Calculate the rental duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    def get_total_cost(self):
        """Calculate the total rental cost"""
        return self.get_duration_days() * self.machine.current_price
    
    @property
    def total_cost(self):
        """Property for template access to total cost"""
        return self.get_total_cost()
    
    def can_be_modified(self):
        """Check if the rental can still be modified"""
        return self.status in ['pending', 'approved']
    
    def can_be_cancelled(self):
        """Check if the rental can be cancelled"""
        return self.status in ['pending', 'approved']
    
    @classmethod
    def check_availability(cls, machine, start_date, end_date, exclude_rental_id=None):
        """
        Check if a machine is available for the given date range.
        Uses the overlap formula: (start < existing_end) AND (end > existing_start)
        
        Args:
            machine: Machine instance
            start_date: Proposed rental start date
            end_date: Proposed rental end date
            exclude_rental_id: Rental ID to exclude (for updates)
        
        Returns:
            tuple: (is_available: bool, conflicting_rentals: QuerySet)
        """
        from django.db.models import Q
        
        # Find overlapping rentals using the standard overlap formula
        # Uses <= and >= to properly detect same-day conflicts
        overlapping = cls.objects.filter(
            machine=machine,
            status__in=['approved', 'pending'],  # Check both approved and pending
            start_date__lte=end_date,  # Existing start is before or on proposed end
            end_date__gte=start_date   # Existing end is after or on proposed start
        )
        
        # Exclude current rental if updating
        if exclude_rental_id:
            overlapping = overlapping.exclude(id=exclude_rental_id)
        
        is_available = not overlapping.exists()
        return is_available, overlapping
    
    def has_conflicts(self):
        """Check if this rental conflicts with other rentals"""
        is_available, conflicts = self.check_availability(
            self.machine,
            self.start_date,
            self.end_date,
            exclude_rental_id=self.id
        )
        return not is_available
    
    @property
    def booking_status_display(self):
        """
        Display booking status in user-friendly format
        Draft → Pending Approval → Confirmed
        """
        if not self.payment_verified:
            return "Draft (Payment Pending)"
        elif self.status == 'pending' and self.payment_verified:
            return "Pending Admin Approval"
        elif self.status == 'approved':
            return "Confirmed"
        elif self.status == 'rejected':
            return "Rejected"
        elif self.status == 'cancelled':
            return "Cancelled"
        elif self.status == 'completed':
            return "Completed"
        return "Unknown"
    
    @property
    def can_be_approved(self):
        """Check if rental can be approved by admin"""
        return (
            self.status == 'pending' and
            self.payment_verified and
            not self.has_conflicts_with_approved()
        )
    
    @property
    def days_until_start(self):
        """Calculate days until rental starts"""
        from datetime import date
        today = date.today()
        if self.start_date > today:
            return (self.start_date - today).days
        return 0
    
    @property
    def days_since_end(self):
        """Calculate days since rental ended"""
        from datetime import date
        today = date.today()
        if self.end_date < today:
            return (today - self.end_date).days
        return 0
    
    def get_transaction_id(self):
        """Get the internal transaction ID from associated payment"""
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        
        try:
            content_type = ContentType.objects.get_for_model(self)
            payment = Payment.objects.filter(
                content_type=content_type,
                object_id=self.id
            ).first()
            
            if payment and payment.internal_transaction_id:
                return payment.internal_transaction_id
        except:
            pass
        
        return None
        today = date.today()
        if self.end_date < today:
            return (today - self.end_date).days
        return 0
    
    @property
    def blocks_machine(self):
        """
        Check if this rental blocks the machine from other bookings
        Only approved rentals block the machine
        """
        return self.status == 'approved'
    
    def get_payment_proof_url(self):
        """Get URL for payment proof file"""
        if self.payment_slip:
            return self.payment_slip.url
        return None
    
    def has_conflicts_with_approved(self):
        """Check if this rental conflicts with APPROVED rentals only"""
        is_available, conflicts = self.check_availability_for_approval(
            self.machine,
            self.start_date,
            self.end_date,
            exclude_rental_id=self.id
        )
        return not is_available
    
    @classmethod
    def check_availability_for_approval(cls, machine, start_date, end_date, exclude_rental_id=None):
        """
        Check availability considering only APPROVED rentals
        Used when admin is approving a new rental
        """
        from django.db.models import Q
        
        overlapping = cls.objects.filter(
            machine=machine,
            status='approved',  # Only check approved rentals
            start_date__lte=end_date,  # <= to detect same-day conflicts
            end_date__gte=start_date   # >= to detect same-day conflicts
        )
        
        if exclude_rental_id:
            overlapping = overlapping.exclude(id=exclude_rental_id)
        
        is_available = not overlapping.exists()
        return is_available, overlapping
    
    @property
    def payment(self):
        """Get associated payment record"""
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self)
        return Payment.objects.filter(content_type=ct, object_id=self.id).first()
    
    @property
    def transaction_id(self):
        """Get internal transaction ID for display"""
        payment = self.payment
        return payment.internal_transaction_id if payment else None

class Maintenance(models.Model):
    MAINTENANCE_TYPE_CHOICES = [
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Maintenance'),
        ('emergency', 'Emergency Repair'),
        ('overhaul', 'Major Overhaul'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='maintenance_records')
    description = models.TextField()
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES, default='preventive')
    issue_reported = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    actual_completion_date = models.DateTimeField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parts_replaced = models.TextField(blank=True, null=True)
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
                                  related_name='assigned_maintenance')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
                                  related_name='reported_maintenance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.machine.name} - {self.get_maintenance_type_display()} ({self.get_status_display()})"
    
    def is_active(self):
        return self.status in ['scheduled', 'in_progress']
    
    def is_overdue(self):
        if self.status in ['scheduled', 'in_progress'] and self.end_date and self.end_date < timezone.now():
            return True
        return False
    
    class Meta:
        ordering = ['-start_date']

class PriceHistory(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.machine.name} - {self.price} ({self.start_date})"
    
    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = 'Price Histories'

class RiceMillAppointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='appointments',
                                limit_choices_to={'machine_type': 'rice_mill'})
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rice_mill_appointments')
    appointment_date = models.DateField()
    time_slot = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Morning (8:00 AM - 12:00 PM)'),
            ('afternoon', 'Afternoon (1:00 PM - 5:00 PM)'),
        ],
        default='morning'
    )
    rice_quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity in kilograms")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reference_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-appointment_date', '-created_at']
        verbose_name = _('Rice Mill Appointment')
        verbose_name_plural = _('Rice Mill Appointments')
        unique_together = ['machine', 'appointment_date', 'time_slot']
    
    def __str__(self):
        return f"{self.machine.name} - {self.user.get_full_name()} ({self.appointment_date} {self.get_time_slot_display()})"
    
    def get_transaction_id(self):
        """Get the internal transaction ID from associated payment"""
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType
        
        try:
            content_type = ContentType.objects.get_for_model(self)
            payment = Payment.objects.filter(
                content_type=content_type,
                object_id=self.id
            ).first()
            
            if payment and payment.internal_transaction_id:
                return payment.internal_transaction_id
        except:
            pass
        
        return None
    
    def can_be_modified(self):
        """Check if the appointment can still be modified"""
        return self.status in ['pending', 'approved'] and self.appointment_date > timezone.now().date()
    
    def can_be_cancelled(self):
        """Check if the appointment can be cancelled"""
        return self.status in ['pending', 'approved'] and self.appointment_date > timezone.now().date()
        
    def save(self, *args, **kwargs):
        """Generate a reference number for new appointments"""
        if not self.reference_number:
            # Generate a unique reference number using date and random numbers
            date_str = timezone.now().strftime('%Y%m%d')
            # Get random 4-digit number
            random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            self.reference_number = f"RM-{date_str}-{random_num}"
            
        super().save(*args, **kwargs)
