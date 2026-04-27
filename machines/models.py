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


def _format_quantity_display(value):
    if value in [None, '']:
        return '0'
    try:
        normalized = Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    formatted = f"{normalized:,.2f}"
    if formatted.endswith('.00'):
        return formatted[:-3]
    if formatted.endswith('0'):
        return formatted[:-1]
    return formatted


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
    MACHINE_CATEGORY_CHOICES = [
        ('tractor', 'Tractor'),
        ('transplanter', 'Transplanter'),
        ('seeder', 'Seeder'),
        ('harvester', 'Harvester'),
        ('thresher', 'Thresher'),
        ('dryer', 'Dryer'),
        ('rice_mill', 'Rice Mill'),
        ('other', 'Other'),
    ]
    MACHINE_TYPE_TO_CATEGORY = {
        'rice_mill': 'rice_mill',
        'tractor_4wd': 'tractor',
        'hand_tractor': 'tractor',
        'transplanter_walking': 'transplanter',
        'transplanter_riding': 'transplanter',
        'precision_seeder': 'seeder',
        'harvester': 'harvester',
        'thresher': 'thresher',
        'flatbed_dryer': 'dryer',
        'solar_dryer': 'dryer',
        'circulating_dryer': 'dryer',
        'other': 'other',
    }
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
            ('thresher', 'Thresher'),
            *DRYER_MACHINE_TYPE_CHOICES,
            ('other', 'Other'),
        ],
        default='other'
    )
    machine_category = models.CharField(
        max_length=20,
        choices=MACHINE_CATEGORY_CHOICES,
        default='other',
    )
    description = models.TextField()
    brand_name = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    model_year = models.PositiveIntegerField(null=True, blank=True)
    horsepower = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
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
    stripe_payment_link = models.URLField(max_length=500, blank=True, null=True, help_text="Legacy online payment link field retained for compatibility.")
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

    @classmethod
    def resolve_machine_category(cls, machine_type):
        return cls.MACHINE_TYPE_TO_CATEGORY.get(machine_type, 'other')

    @classmethod
    def is_machine_category_value(cls, value):
        return value in dict(cls.MACHINE_CATEGORY_CHOICES)

    @classmethod
    def get_machine_category_label(cls, value):
        return dict(cls.MACHINE_CATEGORY_CHOICES).get(value, value.replace('_', ' ').title() if value else 'Other')

    @property
    def resolved_machine_category(self):
        return self.machine_category or self.resolve_machine_category(self.machine_type)
    
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
        """True if there is an active schedule-blocking rental covering today."""
        today = timezone.localdate()
        return any(
            rental.is_schedule_blocking and rental.overlaps_schedule(today, today)
            for rental in self.rentals.exclude(workflow_state__in=['completed', 'cancelled'])
        )
    
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
        if self.machine_type == 'thresher':
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
        elif self.machine_type == 'thresher' or self.name == 'Thresher':
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

    def get_package_price_preview(self, *, area=None, default_days=1, hourly_area_factor=5):
        pricing = self.get_pricing_info()
        unit = pricing.get('unit') or self._default_pricing_unit()
        rate = pricing.get('rate')
        rate_decimal = None if rate is None else Decimal(str(rate)).quantize(Decimal('0.01'))

        area_decimal = None
        if area not in [None, '']:
            try:
                area_decimal = Decimal(str(area))
            except (InvalidOperation, ValueError, TypeError):
                area_decimal = None

        preview = {
            'mode': 'rate_only',
            'unit': unit,
            'rate': str(rate_decimal) if rate_decimal is not None else '',
            'rate_display': self.get_rate_display(),
            'estimate_label': 'Rate only',
            'estimate_value': '',
            'formula': self.get_rate_display(),
            'note': 'Review the configured machine rate.',
            'area': str(area_decimal) if area_decimal is not None else '',
            'default_days': int(default_days),
            'hourly_area_factor': int(hourly_area_factor),
        }

        if unit == 'until_dried':
            preview.update({
                'mode': 'rate_only_until_dried',
                'formula': 'Configured as Until dried',
                'note': 'Final billing depends on the completed drying service.',
            })
            return preview

        if rate_decimal is None:
            preview.update({
                'mode': 'unavailable',
                'formula': 'Price not set',
                'note': 'This machine does not have a usable numeric rate yet.',
            })
            return preview

        if unit == 'hectare':
            preview.update({
                'mode': 'per_hectare',
                'formula': f'PHP {rate_decimal:,.2f} x hectares',
                'note': 'Estimated using the package land area in hectares.',
            })
            if area_decimal is not None and area_decimal > 0:
                estimate = (rate_decimal * area_decimal).quantize(Decimal('0.01'))
                preview.update({
                    'estimate_label': 'Estimated total',
                    'estimate_value': str(estimate),
                    'formula': f'PHP {rate_decimal:,.2f} x {area_decimal:,.4f} hectare(s) = PHP {estimate:,.2f}',
                })
            return preview

        if unit == 'flat':
            preview.update({
                'mode': 'flat_fee',
                'estimate_label': 'Estimated total',
                'estimate_value': str(rate_decimal),
                'formula': f'Flat fee = PHP {rate_decimal:,.2f}',
                'note': 'This service uses one fixed charge regardless of area.',
            })
            return preview

        if unit == 'day':
            estimate = (rate_decimal * Decimal(str(default_days))).quantize(Decimal('0.01'))
            preview.update({
                'mode': 'per_day',
                'estimate_label': 'Estimated total',
                'estimate_value': str(estimate),
                'formula': f'PHP {rate_decimal:,.2f} x {default_days} day(s) = PHP {estimate:,.2f}',
                'note': 'Initial package estimate uses one day. Final total may change after schedule confirmation.',
            })
            return preview

        if unit == 'hour':
            preview.update({
                'mode': 'hourly_area_assumption',
                'formula': f'PHP {rate_decimal:,.2f} per hour',
                'note': f'Estimated using the current system assumption of {hourly_area_factor} hours per hectare.',
            })
            if area_decimal is not None and area_decimal > 0:
                estimated_hours = max(1, round(float(area_decimal * Decimal(str(hourly_area_factor)))))
                estimate = (rate_decimal * Decimal(str(estimated_hours))).quantize(Decimal('0.01'))
                preview.update({
                    'estimate_label': 'Estimated total',
                    'estimate_value': str(estimate),
                    'formula': f'PHP {rate_decimal:,.2f} x {estimated_hours} hour(s) = PHP {estimate:,.2f}',
                })
            return preview

        if unit == 'sack':
            preview.update({
                'mode': 'rate_only_sack',
                'formula': f'Configured as {self.get_rate_display()}',
                'note': 'Final cost depends on the actual sack quantity during scheduling or harvest.',
            })
            if self.machine_type == 'harvester':
                preview['note'] = 'Final charge or share depends on the actual harvest yield and sack quantity.'
            return preview

        if unit == 'kg':
            preview.update({
                'mode': 'rate_only_kg',
                'formula': f'Configured as {self.get_rate_display()}',
                'note': 'Final cost depends on the actual kilogram quantity.',
            })
            return preview

        preview.update({
            'mode': 'rate_only_generic',
            'formula': f'Configured as {self.get_rate_display()}',
            'note': 'Review the machine setup for the exact billing basis.',
        })
        return preview
    
    def save(self, *args, **kwargs):
        self.machine_category = self.resolve_machine_category(self.machine_type)
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
        payment_methods = []
        if self.allow_online_payment:
            payment_methods.append("Gcash payment")
        if self.allow_face_to_face_payment:
            payment_methods.append("Over the counter")

        if payment_methods:
            return " or ".join(payment_methods)
        return "Payment method not set"

    def get_settlement_summary(self):
        if self.settlement_type:
            return self.get_settlement_type_display()
        return "Settlement not set"

    def _current_rental_flag(self):
        current_rental_value = getattr(self, 'is_currently_rented', False)
        if callable(current_rental_value):
            return current_rental_value()
        return bool(current_rental_value)

    def get_list_status_summary(self):
        if self.status == 'maintenance':
            return self.get_status_display()
        if self._current_rental_flag():
            return "In use"
        if self.status == 'available':
            return "Available"
        return self.get_status_display()

    def get_card_note(self):
        if self.rental_price_type == 'in_kind':
            return "Settlement after harvest under non-cash payment terms."
        if self.allow_online_payment or self.allow_face_to_face_payment:
            return self.get_payment_summary()
        return "Payment method not set by admin."

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

    @staticmethod
    def _safe_file_url(field_file):
        """Return a file URL only when the underlying media file still exists."""
        if not field_file or not getattr(field_file, 'name', ''):
            return None

        try:
            if field_file.storage.exists(field_file.name):
                return field_file.url
        except Exception:
            return None

        return None
    
    def get_display_image_url(self):
        """Return the URL of the primary image or the first available image"""
        # First, check if there's a primary image
        for image in self.images.filter(is_primary=True):
            image_url = self._safe_file_url(image.image)
            if image_url:
                return image_url
        
        # If no primary image, check if there are any other images
        for image in self.images.all():
            image_url = self._safe_file_url(image.image)
            if image_url:
                return image_url
        
        # Finally, check if there's a direct image
        image_url = self._safe_file_url(self.image)
        if image_url:
            return image_url
        
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

    def get_image_url(self):
        """Return a usable URL only when the image file exists in storage."""
        if not self.image or not getattr(self.image, 'name', ''):
            return None

        try:
            if self.image.storage.exists(self.image.name):
                return self.image.url
        except Exception:
            return None

        return None
    
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
        ('partially_settled', 'Partially Settled'),
        ('paid', 'Paid'),
        ('paid_in_kind', 'PAID (NON-CASH PAYMENT)'),
    ]
    RENTAL_SETTLEMENT_STATUS_CHOICES = [
        ('to_be_determined', 'TO BE DETERMINED'),
        ('pending', 'Pending'),
        ('waiting_for_delivery', 'WAITING FOR DELIVERY'),
        ('partially_settled', 'PARTIALLY SETTLED'),
        ('paid', 'PAID'),
        ('cancelled', 'Cancelled'),
    ]
    WORKFLOW_STATE_CHOICES = [
        ('requested', 'Requested'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ready_for_payment', 'Ready for Payment'),
        ('ready_for_operation', 'Ready for Operation'),
        ('in_progress', 'In Progress'),
        ('overdue', 'Overdue'),
        ('conflict_review', 'Conflict Review'),
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
        if self.start_date is None or self.end_date is None:
            return 0
        return (self.end_date - self.start_date).days + 1

    @property
    def is_terminal_state(self):
        return (
            self.status in {'completed', 'cancelled', 'rejected'}
            or self.workflow_state in {'completed', 'cancelled'}
            or (self.payment_type == 'in_kind' and self.settlement_status == 'paid')
        )

    @property
    def is_schedule_blocking(self):
        if self.is_terminal_state:
            return False
        return self.status == 'approved'

    @property
    def is_overdue_active(self):
        if not self.is_schedule_blocking:
            return False
        if self.actual_return_at:
            return False
        if not self.end_date:
            return False
        return timezone.localdate() > self.end_date

    @property
    def effective_end_date(self):
        if not self.end_date:
            return None
        if self.is_overdue_active:
            return timezone.localdate()
        return self.end_date

    @property
    def overdue_days(self):
        if not self.is_overdue_active or not self.end_date:
            return 0
        return (timezone.localdate() - self.end_date).days

    def overlaps_schedule(self, start_date, end_date):
        effective_end = self.effective_end_date or self.end_date
        if not self.start_date or not effective_end:
            return False
        return self.start_date <= end_date and effective_end >= start_date
    
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

    @property
    def is_payment_settled(self):
        payment = self.payment
        if self.payment_type == 'in_kind':
            return bool(
                self.settlement_status == 'paid'
                or self.status == 'completed'
                or self.workflow_state == 'completed'
            )
        return bool(
            self.payment_verified
            or self.payment_status in {'paid', 'paid_in_kind'}
            or (payment and payment.status == 'completed')
        )

    @property
    def payment_progress_label(self):
        if self.payment_type == 'in_kind':
            if self.workflow_state == 'ready_for_operation':
                return 'Ready for operation'
            if self.is_payment_settled:
                return 'Rice share settled'
            if self.settlement_status == 'partially_settled':
                return 'Partial rice delivery recorded'
            if self.settlement_status == 'waiting_for_delivery':
                return 'Waiting for rice delivery'
            if self.workflow_state == 'harvest_report_submitted':
                return 'Harvest recorded'
            if self.workflow_state == 'in_progress':
                return 'In operation'
            return 'After harvest settlement'
        if self.workflow_state == 'ready_for_payment':
            return 'Ready for payment'
        if self.is_payment_settled:
            return 'Paid'
        if self.payment_verified and self.workflow_state == 'in_progress':
            return 'In operation'
        if self.payment_method == 'online':
            if self.payment_date or self.stripe_session_id:
                return 'Payment submitted, waiting for verification'
            return 'Waiting for Gcash payment'
        if self.payment_method == 'face_to_face':
            return 'For over-the-counter payment'
        return 'Payment method to be finalized'

    @property
    def payment_list_badge_label(self):
        if self.payment_type == 'in_kind':
            return 'Rice Share'
        if self.payment_method == 'online':
            return 'Online'
        if self.payment_method == 'face_to_face':
            return 'Over the Counter'
        return 'Payment Pending'

    @property
    def payment_list_badge_variant(self):
        if self.payment_type == 'in_kind':
            return 'inkind'
        if self.payment_method == 'online':
            return 'online'
        if self.payment_method == 'face_to_face':
            return 'f2f'
        return 'pending'

    @property
    def payment_list_detail(self):
        if self.payment_type == 'in_kind':
            required_share = self.required_bufia_share
            received_share = self.rice_delivered
            if required_share and received_share:
                return (
                    f"{_format_quantity_display(received_share)} of "
                    f"{_format_quantity_display(required_share)} sacks delivered"
                )
            if required_share:
                return f"{_format_quantity_display(required_share)} sacks due"
            if self.workflow_state == 'harvest_report_submitted':
                return 'Harvest reported, waiting for rice delivery'
            return 'After harvest settlement'

        amount = self.display_payment_amount
        if amount in [None, '']:
            return 'To be determined'
        normalized_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        if normalized_amount <= Decimal('0.00') and not self.is_payment_settled:
            return 'To be determined'
        return f"PHP {normalized_amount:,.2f}"

    @property
    def can_start_online_payment(self):
        base_eligibility = bool(
            self.payment_type != 'in_kind'
            and self.payment_method == 'online'
            and self.status == 'approved'
            and not self.payment_verified
            and self.payment_status != 'paid'
            and not self.payment_date
            and not self.stripe_session_id
        )
        if not base_eligibility:
            return False

        package_item = getattr(self, 'package_item', None)
        if package_item and package_item.rental_package_id:
            return self.workflow_state == 'ready_for_payment'

        return True

    def calculate_payment_amount(self):
        """
        Canonical rental amount calculator based on the machine pricing unit.
        """
        if self.payment_type == 'in_kind':
            return Decimal('0.00')
        if not self.machine_id:
            return Decimal('0.00')
        pricing = self.machine.get_pricing_info()
        parsed_rate = pricing.get('rate', Decimal('0'))
        pricing_unit = pricing.get('unit') or self.machine._default_pricing_unit()

        try:
            rate = Decimal(str(parsed_rate))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')

        if pricing_unit == 'flat':
            amount = rate
        elif pricing_unit == 'day':
            amount = rate * Decimal(str(self.get_duration_days()))
        elif pricing_unit == 'hectare':
            if self.area is None:
                return Decimal('0.00')
            try:
                amount = rate * Decimal(str(self.area))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal('0.00')
        elif pricing_unit in ('kg', 'sack', 'hour'):
            if self.area is None:
                return Decimal('0.00')
            try:
                amount = rate * Decimal(str(self.area))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal('0.00')
        else:
            if self.area is None:
                return Decimal('0.00')
            try:
                amount = rate * Decimal(str(self.area))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal('0.00')

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
        if self.workflow_state == 'overdue':
            return 'Overdue'
        if self.workflow_state == 'conflict_review':
            return 'Conflict Review'
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
            'thresher',
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
        return cls._check_machine_schedule_availability(
            machine,
            start_date,
            end_date,
            exclude_rental_id=exclude_rental_id,
        )

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
        if self.workflow_state == 'overdue':
            return "Overdue"
        if self.workflow_state == 'conflict_review':
            return "Conflict Review"
        if self.workflow_state == 'ready_for_payment':
            return "Ready for Payment"
        if self.workflow_state == 'ready_for_operation':
            return "Ready for Operation"
        if self.payment_type == 'in_kind':
            if self.status == 'pending':
                return "Pending Admin Approval (Non-cash payment)"
            if self.status == 'approved':
                if self.workflow_state == 'harvest_report_submitted' or self.settlement_status in {'waiting_for_delivery', 'partially_settled'}:
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
    def receipt_available(self):
        if self.payment_type == 'in_kind':
            return self.settlement_status == 'paid' or self.status == 'completed' or self.workflow_state == 'completed'
        return bool(
            self.payment_verified
            or self.payment_date
            or self.payment_status in {'paid', 'paid_in_kind'}
        )
    
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
        based on the active workflow, not only the original end date.
        """
        return self.is_schedule_blocking
    
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
        return cls._check_machine_schedule_availability(
            machine,
            start_date,
            end_date,
            exclude_rental_id=exclude_rental_id,
        )

    @classmethod
    def _check_machine_schedule_availability(cls, machine, start_date, end_date, exclude_rental_id=None):
        from django.db.models import Q

        latest_relevant_start = max(end_date, timezone.localdate())
        candidates = cls.objects.filter(
            machine=machine,
            status='approved',
            start_date__lte=latest_relevant_start,
        ).exclude(
            Q(status__in=['completed', 'cancelled', 'rejected']) |
            Q(workflow_state__in=['completed', 'cancelled'])
        )

        if exclude_rental_id:
            candidates = candidates.exclude(id=exclude_rental_id)

        overlapping_ids = [
            rental.id for rental in candidates
            if rental.is_schedule_blocking and rental.overlaps_schedule(start_date, end_date)
        ]
        overlapping = cls.objects.filter(id__in=overlapping_ids).select_related('machine', 'user')
        return not overlapping_ids, overlapping

    @classmethod
    def sync_overdue_workflow_states(cls, *, today=None):
        today = today or timezone.localdate()
        active_rentals = list(
            cls.objects.select_related('machine', 'user').filter(status='approved').exclude(
                Q(status__in=['completed', 'cancelled', 'rejected']) |
                Q(workflow_state__in=['completed', 'cancelled'])
            )
        )

        updated_ids = []

        def _set_workflow_state(rental, new_state):
            if rental.workflow_state == new_state:
                return
            cls.objects.filter(pk=rental.pk).update(
                workflow_state=new_state,
                updated_at=timezone.now(),
            )
            rental.workflow_state = new_state
            updated_ids.append(rental.id)

        overdue_rentals = []
        for rental in active_rentals:
            if rental.actual_return_at:
                continue
            if rental.end_date and today > rental.end_date:
                overdue_rentals.append(rental)
                _set_workflow_state(rental, 'overdue')

        overdue_by_machine = {}
        for rental in overdue_rentals:
            overdue_by_machine.setdefault(rental.machine_id, []).append(rental)

        for rental in active_rentals:
            if rental.id in updated_ids:
                rental.workflow_state = 'overdue'

            if rental.is_terminal_state or rental.status != 'approved':
                continue

            if rental.machine_id not in overdue_by_machine:
                if rental.workflow_state == 'conflict_review':
                    _set_workflow_state(rental, 'approved')
                continue

            if any(
                overdue.id != rental.id and overdue.overlaps_schedule(rental.start_date, rental.end_date)
                for overdue in overdue_by_machine[rental.machine_id]
            ):
                _set_workflow_state(rental, 'conflict_review')
            elif rental.workflow_state == 'conflict_review':
                _set_workflow_state(rental, 'approved')

        return updated_ids
    
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
                if self.workflow_state == 'harvest_report_submitted' or self.settlement_status in {'waiting_for_delivery', 'partially_settled'} or self.required_bufia_share:
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
        max_length=50,  # Increased from 20 to accommodate FLEX-RM-YYYYMMDD-XXXX format
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


class RentalPackage(models.Model):
    PACKAGE_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('partially_scheduled', 'Partially Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('not_required', 'Not Required Yet'),
    ]
    PAYMENT_PREFERENCE_CHOICES = [
        ('', 'To Be Determined'),
        ('online', 'Gcash Payment'),
        ('face_to_face', 'Over the Counter'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_packages',
    )
    package_name = models.CharField(max_length=150, default='Whole Farming Service Package')
    farmer_name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    area = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    preferred_start_date = models.DateField()
    preferred_timeline_notes = models.CharField(max_length=255, blank=True)
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=PACKAGE_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_preference = models.CharField(max_length=20, choices=PAYMENT_PREFERENCE_CHOICES, blank=True, default='')
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_rental_packages',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Rental Package')
        verbose_name_plural = _('Rental Packages')

    def __str__(self):
        return f'{self.package_name} - {self.farmer_name} ({self.preferred_start_date})'

    @property
    def scheduled_items_count(self):
        return self.items.exclude(status='not_included').filter(
            status__in=['scheduled', 'tentative', 'in_progress', 'completed']
        ).count()

    @property
    def included_items_count(self):
        return self.items.exclude(status='not_included').count()

    @property
    def has_in_kind_items(self):
        return any(
            item.is_in_kind_pricing
            for item in self.items.exclude(status__in=['not_included', 'cancelled']).select_related('machine')
        )

    @property
    def total_amount_display(self):
        included_items = list(
            self.items.exclude(status__in=['not_included', 'cancelled']).select_related('machine')
        )
        if not included_items:
            return 'PHP 0.00'

        cash_total = sum(
            (item.subtotal or Decimal('0.00'))
            for item in included_items
            if not item.is_in_kind_pricing
        ).quantize(Decimal('0.01'))

        if cash_total > 0:
            return f'PHP {cash_total:,.2f}'
        if any(item.is_in_kind_pricing for item in included_items):
            return 'Non-cash after harvest'
        return f'PHP {self.total_amount:,.2f}'

    def refresh_total_amount(self, save=True):
        total = sum((item.subtotal or Decimal('0.00') for item in self.items.all()), Decimal('0.00'))
        self.total_amount = total.quantize(Decimal('0.01'))
        if save:
            self.save(update_fields=['total_amount', 'updated_at'])
        return self.total_amount

    def refresh_payment_status(self, save=True):
        included_items = list(
            self.items.exclude(status__in=['not_included', 'cancelled']).select_related('linked_rental')
        )
        if not included_items:
            payment_status = 'not_required'
        else:
            active_linked_rentals = [
                item.linked_rental
                for item in included_items
                if (
                    item.linked_rental_id
                    and item.linked_rental
                    and item.linked_rental.status not in {'cancelled', 'rejected'}
                    and item.linked_rental.workflow_state != 'cancelled'
                )
            ]
            active_linked_ids = {rental.id for rental in active_linked_rentals if rental and rental.id}
            unresolved_items = sum(
                1
                for item in included_items
                if not item.linked_rental_id or item.linked_rental_id not in active_linked_ids
            )
            total_obligations = len(active_linked_rentals) + unresolved_items
            settled_count = sum(1 for rental in active_linked_rentals if rental.is_payment_settled)

            if total_obligations > 0 and settled_count == total_obligations:
                payment_status = 'paid'
            elif settled_count > 0:
                payment_status = 'partially_paid'
            else:
                payment_status = 'pending'

        self.payment_status = payment_status
        if save:
            self.save(update_fields=['payment_status', 'updated_at'])
        return self.payment_status

    def update_status_from_items(self, save=True):
        included_items = list(self.items.exclude(status='not_included'))
        if not included_items:
            self.status = 'pending'
        elif all(item.status == 'completed' for item in included_items):
            self.status = 'completed'
        elif any(item.status == 'in_progress' for item in included_items):
            self.status = 'in_progress'
        elif any(item.status in ['scheduled', 'tentative'] for item in included_items):
            if all(item.status in ['scheduled', 'completed'] for item in included_items):
                self.status = 'approved'
            else:
                self.status = 'partially_scheduled'
        elif all(item.status == 'cancelled' for item in included_items):
            self.status = 'cancelled'
        else:
            self.status = 'pending'
        if save:
            self.save(update_fields=['status', 'updated_at'])
        return self.status


class RentalPackageItem(models.Model):
    SERVICE_CODE_CHOICES = [
        ('tractor', 'Tractor / Plowing'),
        ('rotavator', 'Rotavator / Land Cultivation'),
        ('planter', 'Planter'),
        ('harvester', 'Harvester'),
        ('thresher', 'Thresher'),
    ]
    ITEM_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('scheduled', 'Scheduled'),
        ('tentative', 'Tentative'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('not_included', 'Not Included'),
    ]
    PRICING_UNIT_CHOICES = [
        ('day', 'Per Day'),
        ('hectare', 'Per Hectare'),
        ('flat', 'Flat Fee'),
        ('sack', 'Per Sack'),
        ('hour', 'Per Hour'),
        ('kg', 'Per Kilogram'),
    ]
    SERVICE_MACHINE_TYPE_MAP = {
        'tractor': 'tractor_4wd',
        'rotavator': 'hand_tractor',
        'planter': 'transplanter_walking',
        'harvester': 'harvester',
        'thresher': 'thresher',
    }

    rental_package = models.ForeignKey(
        RentalPackage,
        on_delete=models.CASCADE,
        related_name='items',
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='package_items',
    )
    linked_rental = models.OneToOneField(
        Rental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='package_item',
    )
    service_code = models.CharField(max_length=20, choices=SERVICE_CODE_CHOICES)
    service_name = models.CharField(max_length=150)
    machine_type_required = models.CharField(max_length=20)
    pricing_unit = models.CharField(max_length=20, choices=PRICING_UNIT_CHOICES, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    suggested_start = models.DateField(null=True, blank=True)
    suggested_end = models.DateField(null=True, blank=True)
    scheduled_start = models.DateField(null=True, blank=True)
    scheduled_end = models.DateField(null=True, blank=True)
    is_tentative = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='requested')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sequence_order = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence_order', 'created_at', 'pk']
        verbose_name = _('Rental Package Item')
        verbose_name_plural = _('Rental Package Items')

    def __str__(self):
        return f'{self.rental_package.package_name} - {self.service_name}'

    @property
    def service_label(self):
        return dict(self.SERVICE_CODE_CHOICES).get(self.service_code, self.service_name)

    def get_reference_machine(self):
        if self.machine_id and self.machine:
            return self.machine
        return self.get_candidate_machine_queryset().first()

    @property
    def is_in_kind_pricing(self):
        machine = self.get_reference_machine()
        return bool(machine and machine.rental_price_type == 'in_kind')

    @property
    def has_confirmed_schedule(self):
        return bool(
            self.machine_id and
            self.scheduled_start and
            self.scheduled_end and
            not self.is_tentative and
            self.status in {'scheduled', 'in_progress', 'completed'}
        )

    @property
    def has_schedule_inputs(self):
        return bool(self.machine_id and self.scheduled_start and self.scheduled_end)

    @property
    def effective_pricing_quantity(self):
        return self.compute_default_quantity()

    @property
    def pricing_unit_label(self):
        return dict(self.PRICING_UNIT_CHOICES).get(self.pricing_unit, self.pricing_unit or 'Unit')

    @property
    def quantity_label_display(self):
        if self.is_in_kind_pricing and self.pricing_unit == 'sack':
            return 'Harvested Sacks'
        labels = {
            'hectare': 'Hectares',
            'day': 'Days',
            'flat': 'Flat Fee',
            'sack': 'Sacks',
            'hour': 'Hours',
            'kg': 'Kilograms',
        }
        return labels.get(self.pricing_unit, 'Quantity')

    @property
    def quantity_source_label(self):
        if self.is_in_kind_pricing and self.pricing_unit == 'sack':
            return 'Enter the projected sacks to be harvested'
        if self.pricing_unit == 'hectare':
            return 'Auto from package area'
        if self.pricing_unit == 'day':
            return 'Auto from scheduled dates'
        if self.pricing_unit == 'flat':
            return 'Flat fee uses one charge'
        return f'Enter the number of {self.pricing_unit_label.lower()}'

    @property
    def quantity_display_value(self):
        quantity = self.effective_pricing_quantity
        if quantity is None:
            return '0'
        normalized = quantity.normalize()
        return str(normalized) if normalized == normalized.to_integral() else f'{quantity}'

    @property
    def pricing_rate_display(self):
        machine = self.get_reference_machine()
        if machine and machine.rental_price_type == 'in_kind':
            return machine.get_rate_display()
        try:
            rate = Decimal(str(self.rate or '0.00')).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            rate = Decimal('0.00')
        return f'PHP {rate:,.2f} / {self.pricing_unit_label.lower()}'

    @property
    def machine_requirement_display(self):
        if Machine.is_machine_category_value(self.machine_type_required):
            return Machine.get_machine_category_label(self.machine_type_required)
        machine_type_labels = dict(Machine._meta.get_field('machine_type').choices)
        return machine_type_labels.get(
            self.machine_type_required,
            self.machine_type_required.replace('_', ' ').title() if self.machine_type_required else 'Machine',
        )

    @property
    def subtotal_formula_display(self):
        if self.is_in_kind_pricing:
            machine = self.get_reference_machine()
            if not machine:
                return 'Non-cash settlement after harvest'
            estimated_share = self.estimated_in_kind_share
            if estimated_share > 0:
                share_label = 'sack' if estimated_share == Decimal('1.00') else 'sacks'
                return (
                    f'Estimated BUFIA share: {estimated_share.normalize()} {share_label} '
                    f'using the {machine.get_in_kind_ratio_display()} ratio'
                )
            return f'Settlement after harvest using the {machine.get_in_kind_ratio_display()} ratio'
        quantity = self.effective_pricing_quantity
        if self.pricing_unit == 'flat':
            return 'Flat fee pricing'
        if self.pricing_unit == 'day' and self.scheduled_start and self.scheduled_end:
            day_count = int(quantity)
            return f'{day_count} day{"s" if day_count != 1 else ""} x PHP {Decimal(str(self.rate or "0.00")):,.2f}'
        if quantity <= 0:
            return 'Waiting for quantity or confirmed schedule'
        return f'{self.quantity_display_value} x PHP {Decimal(str(self.rate or "0.00")):,.2f}'

    @property
    def estimated_in_kind_share(self):
        if not self.is_in_kind_pricing:
            return Decimal('0.00')

        machine = self.get_reference_machine()
        if not machine:
            return Decimal('0.00')

        quantity = self.compute_default_quantity()
        if quantity <= 0:
            return Decimal('0.00')

        farmer_share = Decimal(str(machine.in_kind_farmer_share or 0))
        org_share = Decimal(str(machine.in_kind_organization_share or 0))
        if farmer_share <= 0 or org_share <= 0:
            return Decimal('0.00')

        return (quantity * org_share / farmer_share).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )

    @property
    def requested_value_display(self):
        if self.is_in_kind_pricing:
            estimated_share = self.estimated_in_kind_share
            if estimated_share > 0:
                share_label = 'sack' if estimated_share == Decimal('1.00') else 'sacks'
                return f'{estimated_share.normalize()} {share_label} BUFIA share'
            return 'After harvest'
        return f'PHP {Decimal(str(self.subtotal or "0.00")):,.2f}'

    @property
    def requested_meta_display(self):
        if self.is_in_kind_pricing:
            return self.subtotal_formula_display
        return self.subtotal_formula_display

    def get_candidate_machine_queryset(self):
        queryset = Machine.objects.exclude(
            status='maintenance',
        )
        if Machine.is_machine_category_value(self.machine_type_required):
            return queryset.filter(machine_category=self.machine_type_required).order_by('name', 'pk')
        return queryset.filter(machine_type=self.machine_type_required).order_by('name', 'pk')

    def resolve_machine_defaults(self):
        machine = self.machine or self.get_candidate_machine_queryset().first()
        if not machine:
            return None
        pricing = machine.get_pricing_info()
        self.pricing_unit = pricing.get('unit') or machine._default_pricing_unit()
        self.rate = Decimal(str(pricing.get('rate') or '0.00')).quantize(Decimal('0.01'))
        return machine

    def compute_default_quantity(self):
        area = self.rental_package.area or Decimal('0.00')
        if self.pricing_unit == 'hectare':
            return Decimal(str(area)).quantize(Decimal('0.0001')) if area else Decimal('0.0000')
        if self.pricing_unit == 'day':
            if self.scheduled_start and self.scheduled_end:
                return Decimal(str((self.scheduled_end - self.scheduled_start).days + 1)).quantize(Decimal('0.0001'))
            return Decimal('1.0000')
        if self.pricing_unit == 'flat':
            return Decimal('1.0000')
        if self.quantity not in [None, Decimal('0.00')]:
            return Decimal(str(self.quantity)).quantize(Decimal('0.0001'))
        return Decimal('0.0000')

    def calculate_subtotal(self):
        try:
            rate = Decimal(str(self.rate or '0.00'))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')

        quantity = self.compute_default_quantity()
        if self.pricing_unit == 'flat':
            return rate.quantize(Decimal('0.01'))
        if quantity <= 0:
            return Decimal('0.00')
        return (rate * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def clean(self):
        super().clean()
        if self.scheduled_start and self.scheduled_end and self.scheduled_end < self.scheduled_start:
            raise ValidationError({'scheduled_end': 'Scheduled end date cannot be before the scheduled start date.'})
        if self.machine_id:
            if Machine.is_machine_category_value(self.machine_type_required):
                if self.machine.resolved_machine_category != self.machine_type_required:
                    raise ValidationError({'machine': 'The selected machine does not match the required service category.'})
            elif self.machine.machine_type != self.machine_type_required:
                raise ValidationError({'machine': 'The selected machine does not match the required service type.'})

    def save(self, *args, **kwargs):
        if not self.service_name:
            self.service_name = self.service_label
        resolved_machine = self.resolve_machine_defaults()
        if self.machine_id is None and resolved_machine and self.status in ['scheduled', 'tentative']:
            self.machine = resolved_machine
        self.subtotal = self.calculate_subtotal()
        super().save(*args, **kwargs)
        self.rental_package.refresh_total_amount(save=True)



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
