from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import math
import os
from django.utils.text import slugify
import random
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import timedelta
from django.db.models import Q, Sum

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
    DRYER_MACHINE_TYPE_CHOICES = [
        ('flatbed_dryer', 'Flatbed Dryer'),
        ('solar_dryer', 'Solar Dryer'),
        ('circulating_dryer', 'Circulating Dryer'),
    ]
    DRYER_MACHINE_TYPES = tuple(choice[0] for choice in DRYER_MACHINE_TYPE_CHOICES)
    DRYER_MACHINE_TYPE_TO_SERVICE = {
        'flatbed_dryer': 'flatbed',
        'solar_dryer': 'solar',
        'circulating_dryer': 'circulating',
    }
    RENTAL_PRICE_TYPE_CHOICES = [
        ('cash', 'Fixed Rate (Cash)'),
        ('in_kind', 'Non-cash payment'),
    ]
    SETTLEMENT_TYPE_CHOICES = [
        ('immediate', 'Immediate'),
        ('after_harvest', 'After Harvest'),
    ]
    DRYER_SERVICE_TYPE_CHOICES = [
        ('flatbed', 'Flatbed Dryer'),
        ('solar', 'Solar Dryer'),
        ('circulating', 'Circulating Dryer'),
    ]
    DRYER_PRICING_TYPE_CHOICES = [
        ('hourly', 'Per Hour'),
        ('per_sack', 'Per Sack'),
        ('until_dried', 'Until Dried'),
    ]

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
            *DRYER_MACHINE_TYPE_CHOICES,
            ('other', 'Other'),
        ],
        default='other'
    )
    description = models.TextField()
    brand_name = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    model_year = models.PositiveIntegerField(null=True, blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('maintenance', 'Under Maintenance'),
            ('rented', 'In Use'),
        ],
        default='available'
    )
    rental_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_price = models.CharField(max_length=100, help_text="Enter price (e.g., '1500', '₱3500/hectare', '1/9 sack')")
    dryer_service_type = models.CharField(max_length=20, choices=DRYER_SERVICE_TYPE_CHOICES, blank=True, default='flatbed')
    dryer_pricing_type = models.CharField(max_length=20, choices=DRYER_PRICING_TYPE_CHOICES, blank=True, default='hourly')
    dryer_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rental_price_type = models.CharField(max_length=20, choices=RENTAL_PRICE_TYPE_CHOICES, default='cash')
    allow_online_payment = models.BooleanField(default=True)
    allow_face_to_face_payment = models.BooleanField(default=True)
    settlement_type = models.CharField(max_length=20, choices=SETTLEMENT_TYPE_CHOICES, default='immediate')
    in_kind_farmer_share = models.PositiveIntegerField(default=9)
    in_kind_organization_share = models.PositiveIntegerField(default=1)
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

    def is_rentable(self):
        """Machine can be scheduled unless it is under maintenance."""
        return self.status != 'maintenance'

    def has_active_maintenance(self):
        return self.maintenance_records.filter(
            status__in=['scheduled', 'in_progress']
        ).exists()

    def has_active_rental(self):
        today = timezone.localdate()
        return self.rentals.exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        ).filter(
            Q(workflow_state='in_progress') |
            Q(operator_status__in=['traveling', 'operating']) |
            Q(status='approved', start_date__lte=today, end_date__gte=today)
        ).exists()

    def get_operational_status(self):
        if self.has_active_maintenance():
            return 'maintenance'
        if self.has_active_rental():
            return 'rented'
        return 'available'

    def sync_status(self, save=True):
        resolved_status = self.get_operational_status()
        if self.status != resolved_status:
            self.status = resolved_status
            if save:
                self.save(update_fields=['status'])
        return self.status

    def is_currently_rented(self):
        """True if there is an approved rental covering today's date."""
        today = timezone.localdate()
        return self.rentals.filter(
            status='approved',
            start_date__lte=today,
            end_date__gte=today
        ).exclude(
            workflow_state__in=['completed', 'cancelled']
        ).exists()
    
    def is_rice_mill(self):
        return self.machine_type == 'rice_mill'

    def is_flatbed_dryer(self):
        return self.is_dryer_service()

    def is_dryer_service(self):
        return self.machine_type in self.DRYER_MACHINE_TYPES

    def get_dryer_machine_type_display_label(self):
        return dict(self.DRYER_MACHINE_TYPE_CHOICES).get(self.machine_type, self.get_dryer_service_type_display())

    def get_effective_dryer_hourly_rate(self):
        if self.dryer_hourly_rate is not None:
            return Decimal(str(self.dryer_hourly_rate)).quantize(Decimal('0.01'))

        parsed_rate, parsed_unit = self._parse_current_price()
        if parsed_rate is not None and (parsed_unit in [None, 'hour']):
            return Decimal(str(parsed_rate)).quantize(Decimal('0.01'))

        return Decimal('150.00')

    def get_effective_dryer_sack_rate(self):
        parsed_rate, parsed_unit = self._parse_current_price()
        if parsed_rate is not None and (parsed_unit in [None, 'sack']):
            return Decimal(str(parsed_rate)).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def _default_pricing_unit(self):
        """Fallback unit when current_price does not specify one explicitly."""
        if self.machine_type in ['tractor_4wd', 'transplanter_walking', 'transplanter_riding', 'precision_seeder']:
            return 'hectare'
        if self.machine_type == 'rice_mill':
            return 'kg'
        if self.is_dryer_service():
            return 'hour'
        if self.machine_type == 'hand_tractor':
            return 'flat'
        if self.machine_type == 'harvester':
            return 'sack'
        return 'day'

    def _parse_current_price(self):
        """
        Parse admin-configured current_price into numeric rate + billing unit.
        Supports values like:
        - "4000"
        - "4000/hectare"
        - "1500/day"
        - "150/hour"
        """
        raw = str(self.current_price or '').strip().lower()
        if not raw:
            return None, None

        unit = None
        if 'hectare' in raw or '/ha' in raw:
            unit = 'hectare'
        elif 'hour' in raw:
            unit = 'hour'
        elif 'kilogram' in raw or '/kg' in raw or ' per kg' in raw or 'kilo' in raw:
            unit = 'kg'
        elif 'flat' in raw:
            unit = 'flat'
        elif 'sack' in raw:
            unit = 'sack'
        elif 'day' in raw:
            unit = 'day'

        number_match = re.search(r'\d+(\.\d+)?', raw.replace(',', ''))
        if not number_match:
            return None, unit

        try:
            return Decimal(number_match.group()), unit
        except (InvalidOperation, ValueError):
            return None, unit
    
    def get_pricing_info(self):
        """Return pricing information based on machine type"""
        if self.is_dryer_service():
            if self.dryer_pricing_type == 'until_dried':
                return {'rate': None, 'unit': 'until_dried'}
            if self.dryer_pricing_type == 'per_sack':
                return {'rate': self.get_effective_dryer_sack_rate(), 'unit': 'sack'}
            return {'rate': self.get_effective_dryer_hourly_rate(), 'unit': 'hour'}

        parsed_rate, parsed_unit = self._parse_current_price()
        if parsed_rate is not None:
            return {
                'rate': parsed_rate,
                'unit': parsed_unit or self._default_pricing_unit()
            }

        if self.machine_type == 'rice_mill':
            fallback_rate = self.rental_fee_per_day
            if fallback_rate in [None, '', Decimal('0'), 0]:
                fallback_rate = Decimal('3.00')
            return {'rate': Decimal(str(fallback_rate)).quantize(Decimal('0.01')), 'unit': 'kg'}
        elif self.name == 'Flatbed dryer' or self.is_dryer_service():
            return {'rate': Decimal('150'), 'unit': 'hour'}
        elif self.machine_type == 'tractor_4wd' or self.name == '4wheel Drive Tractor':
            return {'rate': Decimal('4000'), 'unit': 'hectare'}
        elif self.machine_type == 'hand_tractor' or self.name == 'Hand tractor':
            return {'rate': Decimal('1000'), 'unit': 'flat'}
        elif self.machine_type in ['transplanter_walking', 'transplanter_riding', 'precision_seeder'] or \
             self.name in ['Walk-behind transplanter', 'Riding Type transplanter', 'Precision Seeder']:
            return {'rate': Decimal('3500'), 'unit': 'hectare'}
        elif self.machine_type == 'harvester' or self.name == 'Harvester':
            return {'rate': Decimal('0'), 'unit': 'sack'}
        else:
            return {'rate': Decimal('0'), 'unit': self._default_pricing_unit()}
    
    def calculate_rental_cost(self, area=1, days=1, yield_amount=0):
        """Calculate rental cost based on machine type and parameters"""
        pricing = self.get_pricing_info()
        
        if pricing['unit'] == 'until_dried':
            return Decimal('0.00')
        if pricing['unit'] == 'hour':
            # For hourly pricing (assuming 5 hours per hectare for now)
            hours = max(1, round(area * 5))
            return pricing['rate'] * hours
        elif pricing['unit'] == 'kg':
            return pricing['rate'] * area
        elif pricing['unit'] == 'hectare':
            # For per hectare pricing
            return pricing['rate'] * area
        elif pricing['unit'] == 'flat':
            # For flat fee pricing
            return pricing['rate']
        elif pricing['unit'] == 'sack':
            if self.machine_type == 'harvester':
                # For harvester, return the number of sacks that will be taken as payment
                if yield_amount <= 0:
                    return "N/A - Need yield estimate"
                return math.ceil(yield_amount / 9)
            # For sack-based dryer pricing, use the provided sack count/quantity.
            if area <= 0:
                return Decimal('0.00')
            return pricing['rate'] * Decimal(str(area))
        else:
            # Default daily rate
            return pricing['rate'] * days
    
    def save(self, *args, **kwargs):
        if self.rental_price_type == 'in_kind':
            self.allow_online_payment = False
            self.allow_face_to_face_payment = False
            self.settlement_type = 'after_harvest'
            self.current_price = "0"
        elif self.is_dryer_service():
            self.dryer_service_type = self.DRYER_MACHINE_TYPE_TO_SERVICE.get(
                self.machine_type,
                self.dryer_service_type or 'flatbed'
            )
            self.dryer_pricing_type = self.dryer_pricing_type or 'hourly'
            if self.dryer_pricing_type == 'hourly':
                dryer_rate = self.get_effective_dryer_hourly_rate()
                self.dryer_hourly_rate = dryer_rate
                self.current_price = f"{dryer_rate.quantize(Decimal('0.01'))}/hour"
                self.rental_fee_per_day = dryer_rate
            elif self.dryer_pricing_type == 'per_sack':
                sack_rate = self.get_effective_dryer_sack_rate()
                self.dryer_hourly_rate = None
                self.current_price = f"{sack_rate.quantize(Decimal('0.01'))}/sack"
                self.rental_fee_per_day = sack_rate
            else:
                self.dryer_hourly_rate = None
                self.current_price = "Until Dried"
                self.rental_fee_per_day = Decimal('0.00')
        if not self.rental_fee_per_day and self.current_price and not (self.is_dryer_service() and self.dryer_pricing_type == 'until_dried'):
            self.rental_fee_per_day = self.current_price
        super().save(*args, **kwargs)

    def get_in_kind_ratio_display(self):
        return f"{self.in_kind_farmer_share}:{self.in_kind_organization_share}"

    def get_rate_display(self):
        """Human-friendly pricing label for machine list/detail pages."""
        if self.rental_price_type == 'in_kind':
            return (
                f"{self.in_kind_organization_share} sack per "
                f"{self.in_kind_farmer_share} sacks harvested"
            )

        if self.is_dryer_service():
            if self.dryer_pricing_type == 'until_dried':
                return 'Until dried'
            if self.dryer_pricing_type == 'per_sack':
                formatted_rate = f"{self.get_effective_dryer_sack_rate():,.2f}"
                return f"PHP {formatted_rate} / sack"
            formatted_rate = f"{self.get_effective_dryer_hourly_rate():,.2f}"
            return f"PHP {formatted_rate} / hour"

        pricing = self.get_pricing_info()
        rate = pricing.get('rate')
        unit = pricing.get('unit') or self._default_pricing_unit()

        if rate is None:
            return self.current_price or "Price not set"

        try:
            formatted_rate = f"{Decimal(str(rate)):,.2f}"
        except (InvalidOperation, ValueError, TypeError):
            return self.current_price or "Price not set"

        unit_display = {
            'kg': 'kg',
            'hour': 'hour',
            'hectare': 'hectare',
            'day': 'day',
            'sack': 'sack',
            'flat': 'flat',
        }.get(unit, unit)

        if unit == 'flat':
            return f"PHP {formatted_rate} flat fee"

        return f"PHP {formatted_rate} / {unit_display}"

    def get_payment_summary(self):
        if self.rental_price_type == 'in_kind':
            return "Non-cash payment after harvest"
        return "Gcash payment or Over the counter"

    def get_machine_summary_details(self):
        """Compact display fields for list/detail pages."""
        details = [
            ("Type", self.get_machine_type_display()),
            ("Status", self.get_status_display()),
            ("Pricing", self.get_rate_display()),
        ]

        if self.rental_price_type == 'in_kind':
            details.append(("Settlement", "After harvest"))
        else:
            details.append(("Payment", self.get_payment_summary()))

        return details
    
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
    CANCELLATION_TYPE_CHOICES = [
        ('', 'Not Cancelled'),
        ('customer', 'Cancelled by Customer'),
        ('admin', 'Cancelled by Admin'),
        ('auto_conflict', 'Auto Cancelled Due to Conflict'),
    ]
    FOLLOW_UP_ACTION_CHOICES = [
        ('none', 'No Follow-up Requested'),
        ('refund_requested', 'Refund Requested'),
        ('reschedule_requested', 'Reschedule Requested'),
        ('refund_processed', 'Refund Processed'),
        ('rescheduled', 'Rescheduled'),
    ]
    RENTAL_PAYMENT_TYPE_CHOICES = [
        ('cash', 'Fixed Rate (Cash)'),
        ('in_kind', 'Non-cash payment'),
    ]
    RENTAL_PAYMENT_STATUS_CHOICES = [
        ('to_be_determined', 'TO BE DETERMINED'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('paid_in_kind', 'PAID (NON-CASH PAYMENT)'),
    ]
    RENTAL_SETTLEMENT_STATUS_CHOICES = [
        ('to_be_determined', 'TO BE DETERMINED'),
        ('pending', 'Pending'),
        ('waiting_for_delivery', 'WAITING FOR DELIVERY'),
        ('paid', 'PAID'),
        ('cancelled', 'Cancelled'),
    ]
    WORKFLOW_STATE_CHOICES = [
        ('requested', 'Requested'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('harvest_report_submitted', 'Harvest Report Submitted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    OPERATOR_STATUS_CHOICES = [
        ('unassigned', 'Unassigned'),
        ('assigned', 'Assigned'),
        ('traveling', 'Traveling'),
        ('operating', 'Operating'),
        ('completed', 'Work Completed'),
        ('harvest_complete', 'Harvest Complete'),
        ('harvest_reported', 'Harvest Reported'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='rentals')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rentals')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_contact_number = models.CharField(max_length=50, blank=True)
    customer_address = models.TextField(blank=True)
    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operator_rentals'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    cancellation_type = models.CharField(
        max_length=20,
        choices=CANCELLATION_TYPE_CHOICES,
        default='',
        blank=True,
    )
    cancel_reason = models.TextField(blank=True)
    system_note = models.TextField(blank=True)
    follow_up_action = models.CharField(
        max_length=30,
        choices=FOLLOW_UP_ACTION_CHOICES,
        default='none',
    )
    follow_up_requested_at = models.DateTimeField(null=True, blank=True)
    follow_up_resolved_at = models.DateTimeField(null=True, blank=True)
    follow_up_admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Rental details
    area = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Land area in hectares"
    )
    
    # Payment fields
    payment_type = models.CharField(max_length=20, choices=RENTAL_PAYMENT_TYPE_CHOICES, default='cash')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=30, choices=RENTAL_PAYMENT_STATUS_CHOICES, default='to_be_determined')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[('online', 'Gcash Payment'), ('face_to_face', 'Over the Counter')],
        null=True,
        blank=True
    )
    payment_slip = models.FileField(upload_to=rental_payment_slip_path, null=True, blank=True)
    payment_verified = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Face-to-face payment details
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Actual amount received")
    or_number = models.CharField(max_length=100, blank=True, help_text="Official Receipt Number")
    payment_notes = models.TextField(blank=True, help_text="Payment recording notes")
    
    field_location = models.CharField(max_length=255, blank=True, null=True)
    settlement_type = models.CharField(max_length=20, choices=Machine.SETTLEMENT_TYPE_CHOICES, default='immediate')
    settlement_status = models.CharField(max_length=30, choices=RENTAL_SETTLEMENT_STATUS_CHOICES, default='to_be_determined')
    total_harvest_sacks = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    organization_share_required = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    organization_share_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    settlement_date = models.DateTimeField(null=True, blank=True)
    settlement_reference = models.CharField(max_length=50, blank=True, null=True)
    transaction_reference = models.CharField(max_length=50, blank=True, null=True)
    receipt_number = models.CharField(max_length=80, blank=True, null=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_rentals'
    )
    
    # IN-KIND Workflow Fields
    workflow_state = models.CharField(
        max_length=30,
        choices=WORKFLOW_STATE_CHOICES,
        default='requested'
    )
    operator_status = models.CharField(
        max_length=30,
        choices=OPERATOR_STATUS_CHOICES,
        default='unassigned'
    )
    operator_notes = models.TextField(blank=True)
    operator_last_update_at = models.DateTimeField(null=True, blank=True)
    operator_reported_at = models.DateTimeField(null=True, blank=True)
    
    # Equipment Operation Tracking
    actual_handover_date = models.DateTimeField(null=True, blank=True)
    actual_completion_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time when rental was completed (for early completions)'
    )
    scheduled_pickup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Planned pickup or handover time for admin overdue tracking.'
    )
    scheduled_return_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Planned return time for admin overdue tracking.'
    )
    actual_pickup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time when the machine was picked up or handed over.'
    )
    actual_return_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time when the machine was returned.'
    )
    
    # Harvest Information
    total_rice_sacks_harvested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total sacks harvested by operator"
    )
    bufia_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="BUFIA's share (1 sack per 9 harvested)"
    )
    member_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Member's share (remaining sacks)"
    )
    
    # Audit Trail
    state_changed_at = models.DateTimeField(auto_now=True)
    state_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rental_state_changes'
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
        return f"{self.machine.name} - {self.customer_display_name} ({self.start_date} to {self.end_date})"

    def clean(self):
        super().clean()

        if not self.machine_id or not self.start_date or not self.end_date:
            return

        # Once a rental is being closed or removed from the active schedule,
        # skip overlap validation so admins can cancel or complete conflicted records.
        if self.status in {'cancelled', 'rejected', 'completed'} or self.workflow_state == 'cancelled':
            return

        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date cannot be before start date.'
            })

        if self.scheduled_pickup_at and self.scheduled_return_at and self.scheduled_return_at < self.scheduled_pickup_at:
            raise ValidationError({
                'scheduled_return_at': 'Scheduled return time cannot be before the scheduled pickup time.'
            })

        if self.actual_pickup_at and self.actual_return_at and self.actual_return_at < self.actual_pickup_at:
            raise ValidationError({
                'actual_return_at': 'Actual return time cannot be before the actual pickup time.'
            })

        is_available, conflicts = self.check_availability(
            machine=self.machine,
            start_date=self.start_date,
            end_date=self.end_date,
            exclude_rental_id=self.pk
        )
        if not is_available:
            conflict = conflicts.first()
            conflict_start = conflict.start_date if conflict else self.start_date
            conflict_end = conflict.end_date if conflict else self.end_date
            raise ValidationError(
                f'{self.machine.name} is already booked from {conflict_start} to {conflict_end}. '
                'Please choose different dates.'
            )
    
    def get_duration_days(self):
        """Calculate the rental duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    def get_total_cost(self):
        """Calculate the total rental cost"""
        return self.calculate_payment_amount()

    @property
    def customer_display_name(self):
        if self.customer_name:
            return self.customer_name
        full_name = self.user.get_full_name() if self.user_id else ''
        return full_name or (self.user.username if self.user_id else 'Unknown')

    @property
    def customer_display_contact_number(self):
        if self.customer_contact_number:
            return self.customer_contact_number
        return getattr(self.user, 'phone_number', '') if self.user_id else ''

    @property
    def customer_display_address(self):
        if self.customer_address:
            return self.customer_address
        return getattr(self.user, 'address', '') if self.user_id else ''

    @property
    def customer_is_walk_in(self):
        return bool(self.user_id and getattr(self.user, 'username', '') == 'system')

    @property
    def customer_source_label(self):
        return 'Walk-in' if self.customer_is_walk_in else 'Member'

    @property
    def customer_display_email(self):
        if self.customer_is_walk_in:
            return ''
        return getattr(self.user, 'email', '') if self.user_id else ''

    @property
    def customer_reference_label(self):
        if self.customer_is_walk_in:
            return 'Walk-in renter'
        username = getattr(self.user, 'username', '') if self.user_id else ''
        return f'@{username}' if username else 'Member account'
    
    @property
    def total_cost(self):
        """Property for template access to total cost"""
        return self.get_total_cost()

    @property
    def display_payment_amount(self):
        """Return a user-facing payment amount even if the stored field is blank."""
        if self.payment_type == 'in_kind':
            return self.payment_amount
        return self.payment_amount if self.payment_amount is not None else self.calculate_payment_amount()

    def calculate_payment_amount(self):
        """
        Canonical rental amount calculator:
        payment = admin-configured machine price x user hectares.
        """
        if self.payment_type == 'in_kind':
            return Decimal('0.00')
        if not self.machine_id or self.area is None:
            return Decimal('0.00')

        parsed_rate, _ = self.machine._parse_current_price()
        if parsed_rate is None:
            pricing = self.machine.get_pricing_info()
            parsed_rate = pricing.get('rate', Decimal('0'))

        try:
            rate = Decimal(str(parsed_rate))
            area = Decimal(str(self.area))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')

        amount = rate * area

        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calculate_harvest_shares(self, total_harvest=None):
        """Return the rounded BUFIA and member shares for a harvest amount."""
        harvest_value = self.total_harvest_sacks if total_harvest is None else total_harvest
        if harvest_value is None:
            return Decimal('0.00'), Decimal('0.00')
        try:
            total = Decimal(str(harvest_value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00'), Decimal('0.00')

        farmer_share = Decimal(str(self.machine.in_kind_farmer_share or 0))
        org_share = Decimal(str(self.machine.in_kind_organization_share or 0))
        if total <= 0 or farmer_share <= 0 or org_share <= 0:
            return Decimal('0.00'), Decimal('0.00')

        bufia_share = (total * org_share / farmer_share).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )
        member_share = (total - bufia_share).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )
        return bufia_share, member_share

    def calculate_rice_share(self):
        """Calculate the BUFIA rice share for in-kind settlements."""
        bufia_share, _ = self.calculate_harvest_shares()
        return bufia_share

    def generate_settlement_reference(self):
        if self.settlement_reference:
            return self.settlement_reference
        year = timezone.now().year
        return f"BUFIA-HRV-{year}-{self.id:04d}"

    def generate_transaction_reference(self):
        if self.transaction_reference:
            return self.transaction_reference
        return f"BUFIA-HRV-{self.id:05d}"

    def save(self, *args, **kwargs):
        # Align rental mode with machine configuration when creating.
        if self.machine_id and not self.pk:
            self.payment_type = self.machine.rental_price_type
            self.settlement_type = self.machine.settlement_type

        if self.payment_type == 'in_kind':
            self.payment_method = None
            self.settlement_type = 'after_harvest'
            if not self.payment_status:
                self.payment_status = 'to_be_determined'
            if not self.settlement_status:
                self.settlement_status = 'to_be_determined'

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def workflow_payment_type(self):
        """Return the user-facing payment type for this rental."""
        if self.payment_type == 'in_kind':
            return 'in_kind'
        if self.payment_method == 'face_to_face':
            return 'face_to_face'
        if self.payment_method == 'online':
            return 'online'
        return 'cash'

    @property
    def workflow_payment_type_display(self):
        labels = {
            'in_kind': 'Non-cash payment',
            'online': 'Gcash Payment',
            'face_to_face': 'Over the Counter',
            'cash': 'Cash Payment',
        }
        return labels.get(self.workflow_payment_type, 'Cash Payment')

    @property
    def workflow_status_display(self):
        if self.status == 'completed' or self.workflow_state == 'completed':
            return 'Completed'
        if self.payment_type == 'in_kind' and self.status == 'approved':
            return 'In Progress'
        if self.workflow_state == 'in_progress':
            return 'In Progress'
        if self.status == 'approved':
            return 'Approved'
        if self.status == 'pending':
            return 'Pending Approval'
        return self.get_status_display()

    @property
    def harvest_total(self):
        return self.total_harvest_sacks or self.total_rice_sacks_harvested

    @property
    def required_bufia_share(self):
        return self.bufia_share or self.organization_share_required

    @property
    def rice_delivered(self):
        return self.organization_share_received

    @property
    def schedule_tracking_closed(self):
        return (
            self.status in {'completed', 'rejected', 'cancelled'} or
            self.workflow_state in {'completed', 'cancelled'}
        )

    def is_pickup_overdue(self, now=None):
        current_time = now or timezone.now()
        return bool(
            self.scheduled_pickup_at and
            not self.actual_pickup_at and
            not self.schedule_tracking_closed and
            self.scheduled_pickup_at <= current_time
        )

    @property
    def pickup_is_overdue(self):
        return self.is_pickup_overdue()

    def is_return_overdue(self, now=None):
        current_time = now or timezone.now()
        return bool(
            self.scheduled_return_at and
            not self.actual_return_at and
            not self.schedule_tracking_closed and
            self.scheduled_return_at <= current_time
        )

    @property
    def return_is_overdue(self):
        return self.is_return_overdue()

    @property
    def has_schedule_tracking(self):
        return any([
            self.scheduled_pickup_at,
            self.scheduled_return_at,
            self.actual_pickup_at,
            self.actual_return_at,
        ])

    @property
    def transaction_date(self):
        if self.payment_type == 'in_kind':
            return self.settlement_date or self.verification_date or self.created_at
        return self.payment_date or self.verification_date or self.created_at

    @property
    def payment_reference(self):
        if self.workflow_payment_type == 'face_to_face':
            return self.receipt_number
        if self.payment_type == 'in_kind':
            return self.transaction_reference or self.settlement_reference
        return self.get_transaction_id

    def sync_machine_status(self):
        """Keep machine availability aligned with the rental workflow."""
        if not self.machine_id:
            return
        self.machine.sync_status()

    @property
    def requires_operator_service(self):
        applicable_machine_types = {
            'tractor_4wd',
            'hand_tractor',
            'transplanter_walking',
            'transplanter_riding',
            'precision_seeder',
            'harvester',
        }
        purpose_text = (self.purpose or '').lower()
        return (
            self.payment_type == 'in_kind' or
            self.machine.machine_type in applicable_machine_types or
            'bufia operator' in purpose_text
        )

    @property
    def operator_dashboard_applicable(self):
        return self.requires_operator_service and self.assigned_operator_id is not None
    
    def can_be_modified(self):
        """Check if the rental can still be modified"""
        return self.status in ['pending', 'approved']
    
    def can_be_cancelled(self):
        """Check if the rental can be cancelled"""
        return self.status in ['pending', 'approved']

    @property
    def is_auto_cancelled(self):
        return self.status == 'cancelled' and self.cancellation_type == 'auto_conflict'

    @property
    def payment_record(self):
        cached_payment = getattr(self, '_payment_record_cache', None)
        if cached_payment is not None:
            return cached_payment
        return self.payment

    @payment_record.setter
    def payment_record(self, value):
        self._payment_record_cache = value

    @property
    def refund_available(self):
        payment = self.payment_record
        return bool(self.status == 'cancelled' and payment and payment.can_accept_refunds)

    @property
    def can_request_refund(self):
        return self.status == 'cancelled' and self.follow_up_action == 'none' and self.refund_available

    @property
    def can_request_reschedule(self):
        return self.status == 'cancelled' and self.follow_up_action == 'none'

    @property
    def can_request_follow_up(self):
        return self.can_request_refund or self.can_request_reschedule

    def mark_cancelled(self, *, cancellation_type, cancel_reason='', system_note='', admin_note=''):
        self.status = 'cancelled'
        self.workflow_state = 'cancelled'
        self.cancellation_type = cancellation_type
        self.cancel_reason = cancel_reason
        self.system_note = system_note
        if admin_note:
            self.follow_up_admin_note = admin_note

    @classmethod
    def get_overlapping_pending_rentals(cls, machine, start_date, end_date, exclude_rental_id=None):
        pending_overlaps = cls.objects.filter(
            machine=machine,
            status='pending',
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if exclude_rental_id:
            pending_overlaps = pending_overlaps.exclude(id=exclude_rental_id)
        return pending_overlaps
    
    @classmethod
    def check_availability(cls, machine, start_date, end_date, exclude_rental_id=None):
        """
        Check if a machine is available for the given date range.
        Only approved bookings should hard-block new requests.
        
        Args:
            machine: Machine instance
            start_date: Proposed rental start date
            end_date: Proposed rental end date
            exclude_rental_id: Rental ID to exclude (for updates)
        
        Returns:
            tuple: (is_available: bool, conflicting_rentals: QuerySet)
        """
        from django.db.models import Q
        
        # Find overlapping approved rentals using the standard overlap formula.
        # Pending requests are intentionally not treated as hard blockers.
        overlapping = cls.objects.filter(
            machine=machine,
            status='approved',
            start_date__lte=end_date,  # Existing start is before or on proposed end
            end_date__gte=start_date   # Existing end is after or on proposed start
        ).exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        )
        
        # Exclude current rental if updating
        if exclude_rental_id:
            overlapping = overlapping.exclude(id=exclude_rental_id)
        
        is_available = not overlapping.exists()
        return is_available, overlapping

    @classmethod
    def get_pending_overlaps(cls, machine, start_date, end_date, exclude_rental_id=None):
        """Return overlapping pending requests for warning-only calendar behavior."""
        pending_overlaps = cls.objects.filter(
            machine=machine,
            status='pending',
            start_date__lte=end_date,
            end_date__gte=start_date
        )

        if exclude_rental_id:
            pending_overlaps = pending_overlaps.exclude(id=exclude_rental_id)

        return pending_overlaps
    
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
        if self.status == 'completed' or self.workflow_state == 'completed' or self.settlement_status == 'paid':
            return "Completed"
        if self.payment_type == 'in_kind':
            if self.status == 'pending':
                return "Pending Admin Approval (Non-cash payment)"
            if self.status == 'approved':
                if self.workflow_state == 'harvest_report_submitted' or self.settlement_status == 'waiting_for_delivery':
                    return "In Progress (Awaiting Rice Delivery)"
                return "In Progress (Awaiting Harvest Settlement)"
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
        payment_ready = self.payment_verified or self.payment_type == 'in_kind'
        return (
            self.status == 'pending' and
            payment_ready and
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
    
    @property
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
        except Exception:
            pass
        
        return None
    
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
        ).exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
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

    @property
    def booking_status_display(self):
        """Display booking status in a workflow-aware format."""
        if self.status == 'completed' or self.workflow_state == 'completed':
            return "Completed"
        if self.payment_type == 'in_kind':
            if self.status == 'pending':
                return "Pending Admin Approval (Non-cash payment)"
            if self.status == 'approved':
                if self.workflow_state == 'harvest_report_submitted' or self.settlement_status == 'waiting_for_delivery' or self.required_bufia_share:
                    return "In Progress (Awaiting Rice Delivery)"
                return "In Progress (Awaiting Harvest Settlement)"
        if self.workflow_state == 'in_progress':
            return "In Progress"
        if self.payment_method == 'online' and self.status == 'approved' and not self.payment_verified:
            return "Approved (Awaiting Gcash Payment Verification)"
        if self.payment_method == 'face_to_face' and self.status == 'approved' and not self.payment_verified:
            return "Approved (Awaiting Over-the-Counter Payment)"
        if not self.payment_verified:
            return "Draft (Payment Pending)"
        if self.status == 'pending' and self.payment_verified:
            return "Pending Admin Approval"
        if self.status == 'approved':
            return "Confirmed"
        if self.status == 'rejected':
            return "Rejected"
        if self.status == 'cancelled':
            return "Cancelled"
        return "Unknown"

    @property
    def can_be_approved(self):
        """Pending requests can be approved as long as dates remain conflict-free."""
        return (
            self.status == 'pending' and
            not self.has_conflicts_with_approved()
        )

    @property
    def get_transaction_id(self):
        """Get the most relevant transaction reference for display."""
        payment = self.payment
        if payment and payment.internal_transaction_id:
            return payment.internal_transaction_id
        return self.transaction_reference or self.settlement_reference or self.receipt_number

    @property
    def transaction_id(self):
        """Alias for the transaction identifier used in templates."""
        return self.get_transaction_id

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
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    actual_completion_date = models.DateTimeField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parts_replaced = models.TextField(blank=True, null=True)
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
                                  related_name='assigned_maintenance')
    technician_name = models.CharField(max_length=100, blank=True)
    repair_summary = models.TextField(blank=True)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    completion_notes = models.TextField(blank=True)
    no_parts_replaced = models.BooleanField(default=False)
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

    def get_display_technician_name(self):
        if self.technician_name:
            return self.technician_name.strip()

        if self.technician:
            return self.technician.get_full_name() or self.technician.username

        description = (self.description or '').strip()
        if 'Technician:' in description:
            technician_part = description.split('Technician:', 1)[1].strip()
            if '\n' in technician_part:
                technician_part = technician_part.split('\n', 1)[0].strip()
            return technician_part

        return ''

    @property
    def display_technician_name(self):
        return self.get_display_technician_name()

    def get_parts_total(self):
        prefetched_parts = getattr(self, '_prefetched_objects_cache', {}).get('parts_used')
        if prefetched_parts is not None:
            return sum(
                (part.subtotal or Decimal('0.00') for part in prefetched_parts),
                Decimal('0.00'),
            )

        return self.parts_used.aggregate(total=Sum('subtotal')).get('total') or Decimal('0.00')

    @property
    def parts_total(self):
        return self.get_parts_total()

    def build_parts_replaced_summary(self):
        part_rows = list(self.parts_used.all().order_by('pk'))
        if not part_rows:
            return ''

        return ', '.join(
            f"{part.part_name} x{part.quantity}" if part.quantity != 1 else part.part_name
            for part in part_rows
        )

    def calculate_actual_cost(self):
        return (
            self.get_parts_total()
            + (self.labor_cost or Decimal('0.00'))
            + (self.other_cost or Decimal('0.00'))
        )

    def sync_completion_totals(self, save=True):
        self.parts_replaced = self.build_parts_replaced_summary() or ''
        self.actual_cost = self.calculate_actual_cost()

        if save and self.pk:
            self.save(update_fields=['parts_replaced', 'actual_cost', 'updated_at'])

        return self.actual_cost
    
    class Meta:
        ordering = ['-start_date']


class MaintenancePartUsed(models.Model):
    maintenance_record = models.ForeignKey(
        Maintenance,
        on_delete=models.CASCADE,
        related_name='parts_used',
    )
    part_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.part_name} x{self.quantity}"

    def clean(self):
        if self.quantity is None and self.unit_price in (None, Decimal('0.00')) and not self.part_name:
            return

        if self.quantity is None or self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0.'})
        if self.unit_price is not None and self.unit_price < 0:
            raise ValidationError({'unit_price': 'Unit price cannot be negative.'})

    def save(self, *args, **kwargs):
        quantity = Decimal(str(self.quantity or 0))
        unit_price = self.unit_price or Decimal('0.00')
        self.subtotal = quantity * unit_price
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Maintenance part used'
        verbose_name_plural = 'Maintenance parts used'

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
    BOOKING_SOURCE_MEMBER = 'member'
    BOOKING_SOURCE_BUFIA_RICE_SHARE = 'bufia_rice_share'
    BOOKING_SOURCE_CHOICES = [
        (BOOKING_SOURCE_MEMBER, 'Member Rice'),
        (BOOKING_SOURCE_BUFIA_RICE_SHARE, 'BUFIA Rice Share'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Gcash Payment'),
        ('face_to_face', 'Over the Counter'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved - Waiting for Payment'),
        ('paid', 'Paid - Waiting for Admin Confirmation'),
        ('confirmed', 'Confirmed'),
        ('ongoing', 'Ongoing'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='appointments',
                                limit_choices_to={'machine_type': 'rice_mill'})
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rice_mill_appointments')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_contact_number = models.CharField(max_length=50, blank=True)
    customer_address = models.TextField(blank=True)
    booking_source = models.CharField(
        max_length=30,
        choices=BOOKING_SOURCE_CHOICES,
        default=BOOKING_SOURCE_MEMBER,
    )
    appointment_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    time_slot = models.CharField(
        max_length=20,
        blank=True,
        default=''
    )
    sacks = models.PositiveIntegerField(default=1, help_text="Number of sacks requested for milling")
    rice_quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity in kilograms")
    final_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Actual milled rice weight in kilograms")
    price_per_kg = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('3.00'))
    sell_tahop = models.BooleanField(default=False)
    tahop_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Tahop weight in kilograms")
    tahop_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Tahop selling price per kilogram")
    tahop_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True
    )
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
        return f"{self.machine.name} - {self.customer_display_name} ({self.appointment_date} {self.display_time_range})"

    @property
    def is_bufia_rice_share(self):
        return self.booking_source == self.BOOKING_SOURCE_BUFIA_RICE_SHARE

    @property
    def customer_display_name(self):
        if self.customer_name:
            return self.customer_name
        full_name = self.user.get_full_name() if self.user_id else ''
        return full_name or (self.user.username if self.user_id else 'Unknown')

    @property
    def customer_display_contact_number(self):
        if self.customer_contact_number:
            return self.customer_contact_number
        return getattr(self.user, 'phone_number', '') if self.user_id else ''

    @property
    def customer_display_address(self):
        if self.customer_address:
            return self.customer_address
        return getattr(self.user, 'address', '') if self.user_id else ''
    
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

    @property
    def effective_price_per_kg(self):
        if self.machine_id:
            pricing = self.machine.get_pricing_info()
            rate = pricing.get('rate')
            if rate is not None and pricing.get('unit') == 'kg':
                return Decimal(str(rate)).quantize(Decimal('0.01'))
        if self.price_per_kg not in [None, '']:
            return Decimal(str(self.price_per_kg)).quantize(Decimal('0.01'))
        return Decimal('3.00')

    @property
    def billable_weight(self):
        if self.final_weight is not None:
            billable_weight = self.final_weight
        elif self.rice_quantity is not None:
            billable_weight = self.rice_quantity
        else:
            billable_weight = Decimal('0.00')
        return (billable_weight or Decimal('0')).quantize(Decimal('0.01'))

    @property
    def computed_milling_amount(self):
        return (self.billable_weight * self.effective_price_per_kg).quantize(Decimal('0.01'))

    @property
    def computed_tahop_total_amount(self):
        if not self.sell_tahop:
            return Decimal('0.00')
        tahop_weight = Decimal(str(self.tahop_weight or '0')).quantize(Decimal('0.01'))
        tahop_price = Decimal(str(self.tahop_price_per_kg or '0')).quantize(Decimal('0.01'))
        return (tahop_weight * tahop_price).quantize(Decimal('0.01'))

    @property
    def computed_total_amount(self):
        return (self.computed_milling_amount + self.computed_tahop_total_amount).quantize(Decimal('0.01'))

    @property
    def estimated_weight(self):
        if self.rice_quantity is not None:
            return self.rice_quantity
        if self.sacks:
            return (Decimal(str(self.sacks)) * Decimal('50.00')).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def duration_hours(self):
        if not self.start_time or not self.end_time:
            return Decimal('0.00')
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        duration_minutes = max(end_minutes - start_minutes, 0)
        return (Decimal(duration_minutes) / Decimal('60')).quantize(Decimal('0.01'))

    @property
    def display_time_range(self):
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%I:%M %p').lstrip('0')} - {self.end_time.strftime('%I:%M %p').lstrip('0')}"
        return 'Flexible daytime arrival'

    @property
    def slot_locked(self):
        return self.status in ['approved', 'paid', 'confirmed', 'ongoing']

    @property
    def payment_confirmed(self):
        return self.status in ['confirmed', 'ongoing', 'completed']

    def can_be_modified(self):
        """Check if the appointment can still be modified"""
        return self.status == 'pending' and self.appointment_date > timezone.now().date()
    
    def can_be_cancelled(self):
        """Check if the appointment can be cancelled"""
        return self.status in ['pending', 'approved'] and self.appointment_date > timezone.now().date()
        
    def save(self, *args, **kwargs):
        """Generate a reference number for new appointments"""
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.update({
                'time_slot',
                'rice_quantity',
                'tahop_weight',
                'tahop_price_per_kg',
                'tahop_total_amount',
                'price_per_kg',
                'total_amount',
            })
            kwargs['update_fields'] = update_fields

        if not self.reference_number:
            # Generate a unique reference number using date and random numbers
            date_str = timezone.now().strftime('%Y%m%d')
            # Get random 4-digit number
            random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            self.reference_number = f"RM-{date_str}-{random_num}"

        if self.start_time and self.end_time:
            self.time_slot = f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
        elif not self.time_slot:
            # Date-based appointments stay flexible, so use a unique non-visible slot token.
            self.time_slot = f"FLEX-{self.reference_number}"

        if self.sacks and (self.rice_quantity is None or self.rice_quantity <= 0):
            self.rice_quantity = (Decimal(str(self.sacks)) * Decimal('50.00')).quantize(Decimal('0.01'))

        if self.sell_tahop:
            if self.tahop_weight not in [None, '']:
                self.tahop_weight = Decimal(str(self.tahop_weight)).quantize(Decimal('0.01'))
            if self.tahop_price_per_kg not in [None, '']:
                self.tahop_price_per_kg = Decimal(str(self.tahop_price_per_kg)).quantize(Decimal('0.01'))
            self.tahop_total_amount = self.computed_tahop_total_amount
        else:
            self.tahop_weight = None
            self.tahop_price_per_kg = None
            self.tahop_total_amount = Decimal('0.00')

        self.price_per_kg = self.effective_price_per_kg
        self.total_amount = self.computed_total_amount

        super().save(*args, **kwargs)


class DryerRental(models.Model):
    FLATBED_MAX_CAPACITY_SACKS = Decimal('150.00')
    CAPACITY_LOCKED_STATUSES = ('approved', 'in_progress', 'paid', 'confirmed', 'ongoing')
    RENTAL_TYPE_CHOICES = [
        ('until_dried', 'Until Dried'),
        ('hourly', 'By Hour'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Gcash Payment'),
        ('face_to_face', 'Over the Counter'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('waiting_confirmation', 'Waiting for Confirmation'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name='dryer_rentals',
        limit_choices_to={'machine_type__in': Machine.DRYER_MACHINE_TYPES}
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dryer_rentals')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_contact_number = models.CharField(max_length=50, blank=True)
    customer_address = models.TextField(blank=True)
    rental_type = models.CharField(max_length=20, choices=RENTAL_TYPE_CHOICES, default='until_dried')
    rental_date = models.DateField()
    goods_description = models.TextField(blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    pricing_type_snapshot = models.CharField(max_length=20, choices=Machine.DRYER_PRICING_TYPE_CHOICES, default='hourly')
    hourly_rate_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requested_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_drying_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estimated_end_date = models.DateField(null=True, blank=True)
    estimated_end_time = models.TimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    estimated_drying_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated number of sun-drying days required for solar dryers."
    )
    solar_drying_notes = models.TextField(
        blank=True,
        help_text="Required setup notes for solar dryers, such as expected sun exposure or drying arrangement."
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parent_rental = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_batches',
    )
    batch_number = models.PositiveIntegerField(default=1)
    batch_total = models.PositiveIntegerField(default=1)
    reference_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rental_date', '-created_at']
        verbose_name = _('Dryer Rental')
        verbose_name_plural = _('Dryer Rentals')

    def __str__(self):
        return f"{self.machine.name} - {self.customer_display_name} ({self.rental_date} {self.display_time_range})"

    @property
    def customer_display_name(self):
        if self.customer_name:
            return self.customer_name
        full_name = self.user.get_full_name() if self.user_id else ''
        return full_name or (self.user.username if self.user_id else 'Unknown')

    @property
    def customer_display_contact_number(self):
        if self.customer_contact_number:
            return self.customer_contact_number
        return getattr(self.user, 'phone_number', '') if self.user_id else ''

    @property
    def customer_display_address(self):
        if self.customer_address:
            return self.customer_address
        return getattr(self.user, 'address', '') if self.user_id else ''

    @property
    def is_hourly_pricing(self):
        if self.rental_type == 'hourly':
            return True
        if self.rental_type == 'until_dried' and (
            self.start_time is not None or self.end_time is not None or self.requested_hours is not None
        ):
            return True
        if not self.rental_type:
            return self.pricing_type_snapshot == 'hourly'
        return False

    @property
    def is_until_dried_pricing(self):
        return not self.is_hourly_pricing

    @property
    def is_per_sack_pricing(self):
        if self.pricing_type_snapshot == 'per_sack':
            return True
        return bool(
            self.machine_id
            and not self.is_hourly_pricing
            and self.machine.dryer_pricing_type == 'per_sack'
        )

    @property
    def pricing_type_label(self):
        if self.is_per_sack_pricing:
            return 'Per Sack'
        if self.is_until_dried_pricing:
            return 'Until Dried'
        return 'By Hour'

    @property
    def is_solar_dryer(self):
        return bool(self.machine_id and self.machine.machine_type == 'solar_dryer')

    @property
    def effective_hourly_rate(self):
        if self.hourly_rate_snapshot is not None:
            return Decimal(str(self.hourly_rate_snapshot)).quantize(Decimal('0.01'))
        if self.machine_id:
            return self.machine.get_effective_dryer_hourly_rate()
        return Decimal('150.00')

    @property
    def duration_hours(self):
        if self.requested_hours is not None:
            return Decimal(str(self.requested_hours)).quantize(Decimal('0.01'))
        if not self.start_time or not self.end_time:
            return Decimal('0.00')
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        duration_minutes = max(end_minutes - start_minutes, 0)
        return (Decimal(duration_minutes) / Decimal('60')).quantize(Decimal('0.01'))

    @property
    def display_time_range(self):
        if self.is_until_dried_pricing:
            return 'Until dried service'
        if not self.start_time or not self.end_time:
            return 'Time to be scheduled'
        return f"{self.start_time.strftime('%I:%M %p').lstrip('0')} - {self.end_time.strftime('%I:%M %p').lstrip('0')}"

    @property
    def estimated_service_end_date(self):
        if self.estimated_end_date:
            return self.estimated_end_date
        if self.is_solar_dryer and self.estimated_drying_days:
            return self.rental_date + timedelta(days=max(self.estimated_drying_days - 1, 0))
        return self.rental_date

    @property
    def estimated_service_end_time(self):
        if self.estimated_end_time:
            return self.estimated_end_time
        if self.is_hourly_pricing and self.end_time:
            return self.end_time
        return None

    @property
    def estimated_service_end_display(self):
        service_end_date = self.estimated_service_end_date
        if not service_end_date:
            return 'Not scheduled'

        date_label = service_end_date.strftime('%b %d, %Y')
        service_end_time = self.estimated_service_end_time
        if service_end_time:
            time_label = service_end_time.strftime('%I:%M %p').lstrip('0')
            return f'{date_label} at {time_label}'
        return date_label

    @staticmethod
    def parse_quantity_to_sacks(raw_quantity):
        raw = str(raw_quantity or '').strip().lower().replace(',', '')
        if not raw:
            return None

        sack_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:sacks?|bags?)', raw)
        number_match = sack_match or re.search(r'(\d+(?:\.\d+)?)', raw)
        if not number_match:
            return None

        try:
            return Decimal(number_match.group(1)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @property
    def quantity_in_sacks(self):
        return self.parse_quantity_to_sacks(self.quantity)

    @property
    def root_batch(self):
        return self.parent_rental or self

    @property
    def is_child_batch(self):
        return bool(self.parent_rental_id)

    @property
    def has_child_batches(self):
        if self.pk is None:
            return False
        return self.child_batches.exists()

    @property
    def is_batch_grouped(self):
        return bool(self.parent_rental_id or self.batch_total > 1 or self.has_child_batches)

    @property
    def batch_label(self):
        return f'Batch {self.batch_number} of {max(self.batch_total, 1)}'

    @property
    def batch_group_reference(self):
        root_batch = self.root_batch
        return root_batch.reference_number or self.reference_number

    def batch_group_members_queryset(self):
        if not self.pk:
            return self.__class__.objects.none()
        root_batch = self.root_batch
        return self.__class__.objects.filter(
            Q(pk=root_batch.pk) | Q(parent_rental_id=root_batch.pk)
        ).select_related('machine', 'user', 'parent_rental').order_by('batch_number', 'rental_date', 'created_at', 'pk')

    @property
    def batch_group_total_sacks(self):
        total_sacks = Decimal('0.00')
        for rental in self.batch_group_members_queryset():
            total_sacks += rental.quantity_in_sacks or Decimal('0.00')
        return total_sacks.quantize(Decimal('0.01'))

    @property
    def uses_flatbed_capacity(self):
        return bool(
            self.machine_id
            and self.machine.machine_type == 'flatbed_dryer'
            and self.is_until_dried_pricing
        )

    @classmethod
    def capacity_rentals_for_date(cls, machine, target_date, exclude_pk=None):
        if not machine or machine.machine_type != 'flatbed_dryer' or not target_date:
            return []

        rentals = cls.objects.filter(
            machine=machine,
            rental_type='until_dried',
            status__in=cls.CAPACITY_LOCKED_STATUSES,
            rental_date__lte=target_date,
        ).select_related('user', 'machine').order_by('rental_date', 'created_at')

        if exclude_pk:
            rentals = rentals.exclude(pk=exclude_pk)

        active_rentals = []
        for rental in rentals:
            quantity_in_sacks = rental.quantity_in_sacks
            if quantity_in_sacks is None or quantity_in_sacks <= 0:
                continue
            if rental.rental_date <= target_date <= rental.estimated_service_end_date:
                active_rentals.append(rental)
        return active_rentals

    @classmethod
    def used_flatbed_capacity_for_date(cls, machine, target_date, exclude_pk=None):
        used_capacity = Decimal('0.00')
        for rental in cls.capacity_rentals_for_date(machine, target_date, exclude_pk=exclude_pk):
            used_capacity += rental.quantity_in_sacks or Decimal('0.00')
        return used_capacity.quantize(Decimal('0.01'))

    @classmethod
    def available_flatbed_capacity_for_date(cls, machine, target_date, exclude_pk=None):
        if not machine or machine.machine_type != 'flatbed_dryer':
            return Decimal('0.00')
        available = cls.FLATBED_MAX_CAPACITY_SACKS - cls.used_flatbed_capacity_for_date(
            machine,
            target_date,
            exclude_pk=exclude_pk,
        )
        return max(available, Decimal('0.00')).quantize(Decimal('0.01'))

    @classmethod
    def first_flatbed_date_with_capacity(cls, machine, requested_sacks, start_date, exclude_pk=None, horizon_days=90):
        if (
            not machine
            or machine.machine_type != 'flatbed_dryer'
            or start_date is None
            or requested_sacks is None
            or requested_sacks <= 0
        ):
            return None

        requested_sacks = Decimal(str(requested_sacks)).quantize(Decimal('0.01'))
        for offset in range(max(horizon_days, 0) + 1):
            target_date = start_date + timedelta(days=offset)
            if cls.available_flatbed_capacity_for_date(machine, target_date, exclude_pk=exclude_pk) >= requested_sacks:
                return target_date
        return None

    @property
    def slot_locked(self):
        return self.status in ['approved', 'paid', 'confirmed', 'in_progress']

    def can_be_modified(self):
        if self.is_batch_grouped:
            return False
        return self.status in ['pending', 'waiting_confirmation'] and self.rental_date >= timezone.now().date()

    def can_be_cancelled(self):
        if self.is_batch_grouped:
            members = list(self.batch_group_members_queryset())
            return bool(members) and all(
                member.status in ['pending', 'waiting_confirmation', 'approved']
                and member.rental_date >= timezone.now().date()
                for member in members
            )
        return self.status in ['pending', 'waiting_confirmation', 'approved'] and self.rental_date >= timezone.now().date()

    def get_transaction_id(self):
        from bufia.models import Payment
        from django.contrib.contenttypes.models import ContentType

        try:
            content_type = ContentType.objects.get_for_model(self)
            payment = Payment.objects.filter(content_type=content_type, object_id=self.id).first()
            if payment and payment.internal_transaction_id:
                return payment.internal_transaction_id
        except Exception:
            pass
        return None

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        tracked_update_fields = set(update_fields) if update_fields is not None else None

        if not self.reference_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            self.reference_number = f"DR-{date_str}-{random_num}"
            if tracked_update_fields is not None:
                tracked_update_fields.add('reference_number')
        if self.machine_id:
            if self.is_hourly_pricing:
                self.rental_type = 'hourly'
                self.pricing_type_snapshot = 'hourly'
                self.hourly_rate_snapshot = self.machine.get_effective_dryer_hourly_rate()
            else:
                self.rental_type = 'until_dried'
                if self.machine.dryer_pricing_type == 'per_sack':
                    self.pricing_type_snapshot = 'per_sack'
                    self.hourly_rate_snapshot = self.machine.get_effective_dryer_sack_rate()
                else:
                    self.pricing_type_snapshot = 'until_dried'
                    if self.hourly_rate_snapshot is None:
                        self.hourly_rate_snapshot = self.machine.get_effective_dryer_hourly_rate()
                self.payment_method = None
                self.start_time = None
                self.end_time = None
                self.requested_hours = None
            if tracked_update_fields is not None:
                tracked_update_fields.update([
                    'rental_type',
                    'pricing_type_snapshot',
                    'hourly_rate_snapshot',
                    'payment_method',
                    'start_time',
                    'end_time',
                    'requested_hours',
                ])

        if self.is_hourly_pricing:
            self.estimated_end_date = self.rental_date
            self.estimated_end_time = self.end_time
            self.total_amount = (self.duration_hours * self.effective_hourly_rate).quantize(Decimal('0.01'))
        else:
            if self.estimated_end_date is None:
                self.estimated_end_time = None
            if self.total_amount is None:
                self.total_amount = Decimal('0.00')
            self.payment_method = None
        if tracked_update_fields is not None:
            tracked_update_fields.update(['estimated_end_date', 'estimated_end_time', 'total_amount'])
            kwargs['update_fields'] = list(tracked_update_fields)
        super().save(*args, **kwargs)



# IN-KIND Rental Workflow Models

class HarvestReport(models.Model):
    """
    Records harvest information reported by operators for IN-KIND rentals.
    Admin records the harvest data from operator communication.
    """
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name='harvest_reports'
    )
    
    # Harvest Data
    total_rice_sacks_harvested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total sacks harvested by operator"
    )
    report_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Admin Recording
    recorded_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_harvest_reports'
    )
    recording_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_harvest_reports'
    )
    verification_notes = models.TextField(blank=True)
    
    # Rejection Handling
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    rejection_timestamp = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-report_timestamp']
        verbose_name = _('Harvest Report')
        verbose_name_plural = _('Harvest Reports')
        indexes = [
            models.Index(fields=['rental', 'is_verified']),
            models.Index(fields=['recorded_by_admin', 'report_timestamp']),
        ]
    
    def __str__(self):
        return f"Harvest Report - Rental {self.rental.id} ({self.total_rice_sacks_harvested} sacks)"


class Settlement(models.Model):
    """
    Records the finalized settlement for IN-KIND rentals.
    Created when harvest report is verified and approved.
    """
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    
    # Settlement Details
    settlement_date = models.DateTimeField(auto_now_add=True)
    bufia_share = models.DecimalField(max_digits=10, decimal_places=2)
    member_share = models.DecimalField(max_digits=10, decimal_places=2)
    total_harvested = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Settlement Reference
    settlement_reference = models.CharField(max_length=50, unique=True)
    
    # Finalization
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='finalized_settlements'
    )
    finalized_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-finalized_at']
        verbose_name = _('Settlement')
        verbose_name_plural = _('Settlements')
        indexes = [
            models.Index(fields=['rental', 'finalized_at']),
            models.Index(fields=['settlement_reference']),
        ]
    
    def __str__(self):
        return f"Settlement {self.settlement_reference} - {self.bufia_share} sacks"


class RentalStateChange(models.Model):
    """
    Audit trail for rental workflow state transitions.
    Records every state change with context and who made the change.
    """
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name='state_changes'
    )
    
    # State Transition
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rental_state_changes_made'
    )
    
    # Context
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = _('Rental State Change')
        verbose_name_plural = _('Rental State Changes')
        indexes = [
            models.Index(fields=['rental', 'changed_at']),
            models.Index(fields=['changed_by', 'changed_at']),
        ]
    
    def __str__(self):
        return f"{self.rental.id}: {self.from_state} → {self.to_state}"

# Import operator models
from .models_operator import Operator, OperatorTask
