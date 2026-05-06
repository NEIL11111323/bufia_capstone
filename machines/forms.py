from django import forms
from .models import (
    Machine,
    Rental,
    Maintenance,
    MaintenancePartUsed,
    PriceHistory,
    MachineImage,
    RiceMillAppointment,
    DryerRental,
    RentalPackage,
    RentalPackageItem,
)
from django.utils import timezone
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.db.models import Q
from django.db import transaction


SEPARATE_SERVICE_MACHINE_TYPES = ('rice_mill', *Machine.DRYER_MACHINE_TYPES)
DRYER_LOCKED_RENTAL_STATUSES = ('approved', 'in_progress', 'paid', 'confirmed', 'ongoing')
ONLINE_PAYMENT_MAX_AMOUNT_PHP = Decimal('999999.99')


def _is_admin_booking_actor(user):
    return bool(user and (user.is_staff or user.is_superuser))


def _display_name_for_user(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _membership_farm_location(user):
    membership = getattr(user, 'membership_application', None)
    if not membership:
        return getattr(user, 'address', '') or ''
    location = membership.bufia_farm_location or membership.farm_location or ''
    if not location:
        # Build from address fields as fallback
        parts = [
            membership.sitio,
            membership.barangay,
            membership.city,
            membership.province,
        ]
        location = ', '.join(p for p in parts if p) or getattr(user, 'address', '') or ''
    return location


def _membership_farm_size(user):
    membership = getattr(user, 'membership_application', None)
    if not membership:
        return None
    return membership.farm_size


def _maintenance_blocking_record(machine):
    if not machine:
        return None
    active_records = list(
        machine.maintenance_records.filter(
            status__in=['scheduled', 'in_progress']
        ).order_by('-start_date', '-pk')
    )
    return next((record for record in active_records if record.status == 'in_progress'), None) or (
        active_records[0] if active_records else None
    )


def _maintenance_block_message(machine):
    record = _maintenance_blocking_record(machine)
    issue_text = ''
    if record:
        issue_text = (record.description or '').strip()
    if issue_text:
        return f'Machine is currently under maintenance: {issue_text}'
    return 'Machine is currently under maintenance and unavailable for booking.'


def _format_sack_value(value):
    if value is None:
        return '0'
    value = Decimal(str(value)).quantize(Decimal('0.01'))
    formatted = f"{value:,.2f}"
    if formatted.endswith('.00'):
        return formatted[:-3]
    if formatted.endswith('0'):
        return formatted[:-1]
    return formatted


def _resolve_member_user(selected_member_id):
    if not selected_member_id:
        return None
    User = get_user_model()
    return User.objects.filter(pk=selected_member_id, is_active=True, is_verified=True).first()


def _get_or_create_system_booking_user():
    User = get_user_model()
    system_user, created = User.objects.get_or_create(
        username='system',
        defaults={
            'email': 'system@bufia.local',
            'password': get_random_string(length=32),
            'first_name': 'System',
            'last_name': 'Booking',
            'is_active': False,
        },
    )
    if created:
        system_user.set_unusable_password()
        system_user.save(update_fields=['password'])
    return system_user


def _machine_type_to_dryer_service_type(machine_type):
    return Machine.DRYER_MACHINE_TYPE_TO_SERVICE.get(machine_type, 'flatbed')


def _build_machine_option_label(machine):
    model_parts = []
    if machine.brand_name:
        model_parts.append(machine.brand_name.strip())
    if machine.model_name:
        model_parts.append(machine.model_name.strip())

    model_label = ' '.join(part for part in model_parts if part).strip()
    if machine.model_year:
        model_label = f'{model_label} ({machine.model_year})' if model_label else f'Model {machine.model_year}'

    if not model_label:
        model_label = machine.get_machine_type_display()

    return f'{machine.name} | {model_label} | {machine.get_rate_display()}'


class MachineSummaryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return _build_machine_option_label(obj)

class MachineForm(forms.ModelForm):
    """Form for creating and updating machines"""
    PRICING_UNIT_CHOICES = [
        ('hectare', 'Per Hectare'),
        ('day', 'Per Day'),
        ('hour', 'Per Hour'),
        ('kg', 'Per Kilogram'),
        ('flat', 'Flat Fee'),
        ('sack', 'Per Sack'),
    ]

    current_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        label='Rental Price',
    )
    pricing_unit = forms.ChoiceField(
        choices=PRICING_UNIT_CHOICES,
        required=False,
        label='Pricing Unit',
    )

    def __init__(self, *args, **kwargs):
        self.is_dryer_setup_flow = kwargs.pop('is_dryer_setup_flow', False)
        self.hide_machine_type = kwargs.pop('hide_machine_type', False)
        super().__init__(*args, **kwargs)
        # These fields are conditionally required based on rental_price_type.
        self.fields['current_price'].required = False
        self.fields['pricing_unit'].required = False
        self.fields['in_kind_farmer_share'].required = False
        self.fields['in_kind_organization_share'].required = False
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter machine name'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Describe the machine, its condition, and what service it is used for'
        })
        self.fields['brand_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter machine brand'
        })
        self.fields['model_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter model name or number'
        })
        self.fields['model_year'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter model year',
            'min': '1900',
            'max': '2100',
            'inputmode': 'numeric',
        })
        self.fields['horsepower'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter horsepower',
            'step': '0.01',
            'min': '0',
            'inputmode': 'decimal',
        })
        self.fields['acquisition_date'].widget = forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'}
        )
        self.fields['acquisition_amount'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter acquisition amount',
            'step': '0.01',
            'min': '0',
            'inputmode': 'decimal',
        })
        self.fields['status'].widget.attrs.update({'class': 'form-select'})
        self.fields['machine_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['dryer_service_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['dryer_pricing_type'].widget = forms.Select(
            attrs={'class': 'form-select'}
        )
        if self.is_dryer_setup_flow:
            setup_pricing_choices = [
                ('hourly', 'Per Hour'),
                ('per_sack', 'Per Sack'),
            ]
            # Keep legacy until-dried records editable without exposing it on new setup flows.
            if self.instance.pk and self.instance.dryer_pricing_type == 'until_dried':
                setup_pricing_choices.append(('until_dried', 'Until Dried (Legacy)'))
            self.fields['dryer_pricing_type'].choices = setup_pricing_choices
        self.fields['dryer_pricing_type'].widget.choices = self.fields['dryer_pricing_type'].choices
        self.fields['dryer_hourly_rate'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter hourly dryer rate, e.g. 150.00',
            'step': '0.01',
            'min': '0',
            'inputmode': 'decimal',
        })
        self.fields['flatbed_max_sack_capacity'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter flatbed sack limit, e.g. 150',
            'step': '0.01',
            'min': '0',
            'inputmode': 'decimal',
        })
        self.fields['current_price'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter rate amount, e.g. 4000.00',
            'step': '0.01',
            'min': '0',
            'inputmode': 'decimal',
        })
        self.fields['pricing_unit'].widget.attrs.update({'class': 'form-select'})
        self.fields['rental_price_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['settlement_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['in_kind_farmer_share'].widget.attrs.update({
            'class': 'form-control',
            'min': '1'
        })
        self.fields['in_kind_organization_share'].widget.attrs.update({
            'class': 'form-control',
            'min': '1'
        })
        self.fields['allow_online_payment'].widget.attrs.update({'class': 'payment-option__input'})
        self.fields['allow_face_to_face_payment'].widget.attrs.update({'class': 'payment-option__input'})
        if self.is_dryer_setup_flow:
            self.fields['machine_type'].choices = Machine.DRYER_MACHINE_TYPE_CHOICES
        if self.hide_machine_type:
            machine_type_value = (
                self.data.get('machine_type')
                or self.initial.get('machine_type')
                or getattr(self.instance, 'machine_type', None)
            )
            self.initial['machine_type'] = machine_type_value
            self.fields['machine_type'].widget = forms.HiddenInput()
        self.fields['current_price'].help_text = (
            'Enter the amount only. Use the Pricing Unit dropdown for per hectare, per day, and other billing types.'
        )
        self.fields['brand_name'].help_text = 'Optional manufacturer or brand for the machine.'
        self.fields['model_name'].help_text = 'Optional model name, code, or serial-friendly identifier.'
        self.fields['model_year'].help_text = 'Optional production or purchase model year.'
        self.fields['horsepower'].help_text = 'Optional engine power rating in horsepower (HP).'
        self.fields['acquisition_date'].help_text = 'Record when BUFIA acquired this machine.'
        self.fields['acquisition_amount'].help_text = 'Record the purchase cost so reports can compare earnings versus cost.'
        self.fields['dryer_service_type'].help_text = 'Classify the dryer service as flatbed, solar, or circulating.'
        self.fields['dryer_pricing_type'].help_text = 'Choose whether this dryer is charged per hour or priced per sack.'
        self.fields['dryer_hourly_rate'].help_text = 'Required only for per-hour dryers.'
        self.fields['flatbed_max_sack_capacity'].help_text = (
            'Set the total sacks this dryer can handle on the same date before new requests are blocked.'
        )
        self.fields['pricing_unit'].help_text = (
            'Choose how the cash rate is billed so pricing stays specific and consistent.'
        )

        machine_type = (
            self.data.get('machine_type')
            or self.initial.get('machine_type')
            or getattr(self.instance, 'machine_type', None)
            or 'other'
        )

        if self.instance.pk:
            if self.instance.is_dryer_service():
                if self.instance.dryer_pricing_type == 'hourly' and self.instance.dryer_hourly_rate is not None:
                    self.initial.setdefault('current_price', self.instance.dryer_hourly_rate)
                    self.initial.setdefault('pricing_unit', 'hour')
                elif self.instance.dryer_pricing_type == 'per_sack':
                    self.initial.setdefault('current_price', self.instance.get_effective_dryer_sack_rate())
                    self.initial.setdefault('pricing_unit', 'sack')
                else:
                    self.initial.setdefault('current_price', '')
                    self.initial.setdefault('pricing_unit', 'hour')
            else:
                parsed_rate, parsed_unit = self.instance._parse_current_price()
                if parsed_rate is not None:
                    self.initial.setdefault('current_price', parsed_rate)
                self.initial.setdefault('pricing_unit', parsed_unit or self._default_pricing_unit(machine_type))
        else:
            default_dryer_pricing = self.initial.get('dryer_pricing_type') or self.data.get('dryer_pricing_type')
            if machine_type in Machine.DRYER_MACHINE_TYPES:
                self.initial.setdefault('pricing_unit', 'sack' if default_dryer_pricing == 'per_sack' else 'hour')
            else:
                self.initial.setdefault('pricing_unit', self._default_pricing_unit(machine_type))
        if machine_type in Machine.DRYER_MACHINE_TYPES and self.initial.get('flatbed_max_sack_capacity') in [None, '']:
            self.initial['flatbed_max_sack_capacity'] = Machine(
                machine_type=machine_type
            ).get_dryer_capacity_limit_sacks()

    def _default_pricing_unit(self, machine_type):
        probe = self.instance if self.instance.pk else Machine(machine_type=machine_type or 'other')
        probe.machine_type = machine_type or getattr(probe, 'machine_type', 'other')
        return probe._default_pricing_unit()

    class Meta:
        model = Machine
        fields = [
            'name', 'brand_name', 'model_name', 'model_year', 'horsepower', 'acquisition_date',
            'acquisition_amount', 'description', 'status', 'machine_type', 'dryer_service_type',
            'dryer_pricing_type', 'dryer_hourly_rate', 'flatbed_max_sack_capacity', 'current_price',
            'rental_price_type', 'allow_online_payment', 'allow_face_to_face_payment',
            'settlement_type', 'in_kind_farmer_share', 'in_kind_organization_share'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'current_price': forms.TextInput(attrs={
                'placeholder': 'e.g., 4000/HECTARE or ₱1500/day or 1/9 sack',
            }),
        }
        labels = {
            'dryer_service_type': 'Dryer Type',
            'dryer_pricing_type': 'Dryer Pricing Type',
            'dryer_hourly_rate': 'Rate Per Hour',
            'flatbed_max_sack_capacity': 'Dryer Sack Capacity',
            'horsepower': 'Horsepower (HP)',
            'current_price': 'Rate Amount',
            'rental_price_type': 'Rental Price Type',
            'allow_online_payment': 'Allow Gcash Payment',
            'allow_face_to_face_payment': 'Allow Over-the-Counter Payment',
            'settlement_type': 'Settlement Type',
            'in_kind_farmer_share': 'Non-cash Farmer Share',
            'in_kind_organization_share': 'Non-cash BUFIA Share',
        }
        help_texts = {
            'current_price': 'Enter price with unit (e.g., "4000/HECTARE", "₱1500/day", "1/9 sack")',
        }
    
    def clean_current_price(self):
        """Validate the numeric cash price."""
        rental_price_type = (
            self.cleaned_data.get('rental_price_type')
            or self.data.get('rental_price_type')
            or getattr(self.instance, 'rental_price_type', None)
        )
        machine_type = (
            self.cleaned_data.get('machine_type')
            or self.data.get('machine_type')
            or getattr(self.instance, 'machine_type', None)
        )
        dryer_pricing_type = (
            self.cleaned_data.get('dryer_pricing_type')
            or self.data.get('dryer_pricing_type')
            or getattr(self.instance, 'dryer_pricing_type', None)
        )
        current_price = self.cleaned_data.get('current_price')
        dryer_hourly_rate = (
            self.cleaned_data.get('dryer_hourly_rate')
            or self.data.get('dryer_hourly_rate')
            or getattr(self.instance, 'dryer_hourly_rate', None)
        )
        if rental_price_type == 'in_kind':
            return current_price or Decimal('0.00')
        if machine_type in Machine.DRYER_MACHINE_TYPES and dryer_pricing_type == 'until_dried':
            return current_price or Decimal('0.00')
        if machine_type in Machine.DRYER_MACHINE_TYPES and dryer_pricing_type == 'hourly':
            if dryer_hourly_rate in [None, '']:
                raise ValidationError('Price field cannot be empty.')
            return Decimal(str(dryer_hourly_rate))
        if machine_type in Machine.DRYER_MACHINE_TYPES and dryer_pricing_type == 'per_sack':
            if current_price in [None, '']:
                raise ValidationError('Rate per sack cannot be empty.')
            return Decimal(str(current_price))
        if current_price in [None, '']:
            raise ValidationError('Price field cannot be empty.')
        return current_price

    def clean(self):
        cleaned_data = super().clean()
        rental_price_type = cleaned_data.get('rental_price_type')
        pricing_unit = cleaned_data.get('pricing_unit')
        machine_type = cleaned_data.get('machine_type') or getattr(self.instance, 'machine_type', None) or 'other'
        dryer_pricing_type = cleaned_data.get('dryer_pricing_type') or getattr(self.instance, 'dryer_pricing_type', 'hourly')
        dryer_hourly_rate = cleaned_data.get('dryer_hourly_rate')
        flatbed_max_sack_capacity = cleaned_data.get('flatbed_max_sack_capacity')

        # Keep ratio fields non-null for both create/update paths.
        farmer_share = cleaned_data.get('in_kind_farmer_share')
        org_share = cleaned_data.get('in_kind_organization_share')
        if farmer_share is None:
            farmer_share = getattr(self.instance, 'in_kind_farmer_share', None) or 9
        if org_share is None:
            org_share = getattr(self.instance, 'in_kind_organization_share', None) or 1
        cleaned_data['in_kind_farmer_share'] = farmer_share
        cleaned_data['in_kind_organization_share'] = org_share

        # Force rice mill to use cash payment and immediate settlement
        if machine_type == 'rice_mill':
            cleaned_data['rental_price_type'] = 'cash'
            cleaned_data['settlement_type'] = 'immediate'
            cleaned_data['pricing_unit'] = pricing_unit or 'kg'
        elif machine_type in Machine.DRYER_MACHINE_TYPES:
            cleaned_data['rental_price_type'] = 'cash'
            cleaned_data['settlement_type'] = 'immediate'
            cleaned_data['dryer_service_type'] = _machine_type_to_dryer_service_type(machine_type)
            if flatbed_max_sack_capacity in [None, '']:
                raise ValidationError({
                    'flatbed_max_sack_capacity': 'Enter how many sacks this dryer can handle.'
                })
            if Decimal(str(flatbed_max_sack_capacity)) <= 0:
                raise ValidationError({
                    'flatbed_max_sack_capacity': 'Dryer sack capacity must be greater than zero.'
                })
            if dryer_pricing_type == 'hourly':
                cleaned_data['pricing_unit'] = 'hour'
                if dryer_hourly_rate in [None, '']:
                    raise ValidationError({'dryer_hourly_rate': 'Rate per hour is required for per-hour dryers.'})
                cleaned_data['current_price'] = dryer_hourly_rate
            elif dryer_pricing_type == 'per_sack':
                cleaned_data['pricing_unit'] = 'sack'
                cleaned_data['dryer_hourly_rate'] = None
                if cleaned_data.get('current_price') in [None, '']:
                    raise ValidationError({'current_price': 'Rate per sack is required for solar dryers.'})
            else:
                cleaned_data['pricing_unit'] = 'hour'
                cleaned_data['dryer_hourly_rate'] = None
                cleaned_data['current_price'] = Decimal('0.00')
        elif rental_price_type == 'in_kind':
            cleaned_data['allow_online_payment'] = False
            cleaned_data['allow_face_to_face_payment'] = False
            cleaned_data['settlement_type'] = 'after_harvest'

            if farmer_share <= 0 or org_share <= 0:
                raise ValidationError('Non-cash share values must be greater than zero.')
        else:
            cleaned_data['pricing_unit'] = pricing_unit or self._default_pricing_unit(machine_type)
        return cleaned_data

    def save(self, commit=True):
        machine = super().save(commit=False)
        rental_price_type = self.cleaned_data.get('rental_price_type')

        # Force rice mill to use cash payment and immediate settlement
        if machine.machine_type == 'rice_mill':
            machine.rental_price_type = 'cash'
            machine.settlement_type = 'immediate'
            machine.flatbed_max_sack_capacity = None
            price_amount = Decimal(str(self.cleaned_data.get('current_price') or '0')).quantize(Decimal('0.01'))
            pricing_unit = self.cleaned_data.get('pricing_unit') or 'kg'
            machine.current_price = f"{price_amount}/{pricing_unit}"
            machine.rental_fee_per_day = price_amount
        elif machine.machine_type in Machine.DRYER_MACHINE_TYPES:
            machine.rental_price_type = 'cash'
            machine.settlement_type = 'immediate'
            machine.dryer_service_type = _machine_type_to_dryer_service_type(machine.machine_type)
            machine.dryer_pricing_type = self.cleaned_data.get('dryer_pricing_type') or 'hourly'
            machine.flatbed_max_sack_capacity = Decimal(
                str(self.cleaned_data.get('flatbed_max_sack_capacity') or '0')
            ).quantize(Decimal('0.01'))
            if machine.dryer_pricing_type == 'hourly':
                price_amount = Decimal(str(self.cleaned_data.get('dryer_hourly_rate') or self.cleaned_data.get('current_price') or '0')).quantize(Decimal('0.01'))
                machine.dryer_hourly_rate = price_amount
                machine.current_price = f"{price_amount}/hour"
                machine.rental_fee_per_day = price_amount
            elif machine.dryer_pricing_type == 'per_sack':
                price_amount = Decimal(str(self.cleaned_data.get('current_price') or '0')).quantize(Decimal('0.01'))
                machine.dryer_hourly_rate = None
                machine.current_price = f"{price_amount}/sack"
                machine.rental_fee_per_day = price_amount
            else:
                machine.dryer_hourly_rate = None
                machine.current_price = 'Until Dried'
                machine.rental_fee_per_day = Decimal('0.00')
        elif rental_price_type == 'in_kind':
            machine.flatbed_max_sack_capacity = None
            machine.current_price = '0'
            machine.rental_fee_per_day = Decimal('0.00')
        else:
            machine.flatbed_max_sack_capacity = None
            price_amount = Decimal(str(self.cleaned_data.get('current_price') or '0')).quantize(Decimal('0.01'))
            pricing_unit = self.cleaned_data.get('pricing_unit') or self._default_pricing_unit(machine.machine_type)
            machine.current_price = f"{price_amount}/{pricing_unit}"
            machine.rental_fee_per_day = price_amount

        if commit:
            machine.save()
            self.save_m2m()
        return machine

class MachineImageForm(forms.ModelForm):
    class Meta:
        model = MachineImage
        fields = ['image', 'is_primary', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Image caption (optional)'}),
        }
        
    def clean(self):
        """Validate the entire form data"""
        cleaned_data = super().clean()
        
        # Make is_primary default to False if it's not provided or empty
        if 'is_primary' not in cleaned_data or cleaned_data.get('is_primary') == '' or cleaned_data.get('is_primary') is None:
            cleaned_data['is_primary'] = False
            
        return cleaned_data
        
    def clean_image(self):
        """Validate the image field"""
        image = self.cleaned_data.get('image')
        
        # Return early if no image provided (could be an existing image being edited)
        if not image:
            return image
            
        # Validate image file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.jfif']
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in valid_extensions:
            raise forms.ValidationError(f'Unsupported file extension: {ext}. Please use JPG, JPEG, JFIF, PNG or GIF images.')
        
        # Validate file size (max 5MB)
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image file is too large. Maximum size is 5MB.')
        
        return image
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Check if this form is marked for deletion - if so, don't process further
        if self.cleaned_data.get('DELETE', False):
            # If the instance has an id and we're marked for deletion, just return the instance
            # The formset will handle the actual deletion
            if instance.pk:
                return instance
            else:
                # If it's a new form but somehow marked for deletion, just return None
                return None
        
        # Handle potential validation issues with is_primary field
        if not hasattr(instance, 'is_primary') or instance.is_primary is None:
            instance.is_primary = False
        
        if commit and instance.image:
            # Create the necessary directories
            if instance.machine and instance.image:
                try:
                    # Ensure base directory exists
                    image_base_dir = os.path.join(settings.MEDIA_ROOT, 'machines', 'images')
                    os.makedirs(image_base_dir, exist_ok=True)
                    
                    # Create machine-specific directory using machine slug
                    from django.utils.text import slugify
                    machine_slug = slugify(instance.machine.name)
                    machine_dir = os.path.join(image_base_dir, machine_slug)
                    os.makedirs(machine_dir, exist_ok=True)
                    
                    # Rename the file to include machine slug for better organization
                    original_name = os.path.basename(instance.image.name)
                    base_name, ext = os.path.splitext(original_name)
                    
                    # If it's a JFIF file, convert extension to jpg for better compatibility
                    if ext.lower() == '.jfif':
                        ext = '.jpg'
                    
                    # Create a unique filename with timestamp to avoid collisions
                    from django.utils import timezone
                    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                    new_filename = f"{machine_slug}_{timestamp}{ext}"
                    
                    # Update the image field to use the new path
                    # This ensures Django's storage system saves it in the right location
                    from django.core.files.base import ContentFile
                    if hasattr(instance.image, 'read'):
                        content = instance.image.read()
                        relative_path = f"machines/images/{machine_slug}/{new_filename}"
                        instance.image.save(relative_path, ContentFile(content), save=False)
                    
                    # Debugging
                    print(f"Saving image for machine {instance.machine.id}: {instance.image}")
                    print(f"Machine directory: {machine_dir}")
                    print(f"New image path: {instance.image.path if instance.image else 'None'}")
                    
                except Exception as e:
                    print(f"Error setting up image directories: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Save the instance
            instance.save()
            
        return instance

# Create a formset for handling multiple images
MachineImageFormSet = inlineformset_factory(
    Machine, 
    MachineImage,
    form=MachineImageForm,
    fields=['image', 'is_primary', 'caption'],
    extra=3,  # Allow up to 3 images
    max_num=3,  # Maximum of 3 images
    can_delete=True,
    validate_max=True,
    absolute_max=3,  # Enforce a hard limit of 3 images
    validate_min=False,  # Don't require a minimum number of forms
    error_messages={
        'too_many_forms': 'You can only upload a maximum of 3 images per machine.',
        'too_few_forms': 'Please provide at least one image for the machine.',
    }
)

class RentalForm(forms.ModelForm):
    """Form for creating and updating rental requests"""
    SERVICE_TYPE_CHOICES = [
        ('', 'Select service...'),
        ('land_preparation', 'Land Preparation / Plowing'),
        ('hauling', 'Hauling / Transport'),
        ('transplanting', 'Transplanting'),
        ('seeding', 'Precision Seeding'),
        ('harvesting', 'Harvesting'),
        ('threshing', 'Threshing'),
        ('other_fieldwork', 'Other Field Work'),
    ]

    MACHINE_SERVICE_DEFAULTS = {
        'tractor_4wd': 'land_preparation',
        'hand_tractor': 'land_preparation',
        'transplanter_walking': 'transplanting',
        'transplanter_riding': 'transplanting',
        'precision_seeder': 'seeding',
        'harvester': 'harvesting',
        'thresher': 'threshing',
    }

    # Additional fields not in the model
    requester_name = forms.CharField(
        max_length=200,
        required=False,
        label='Your Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    selected_member_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    requester_contact_number = forms.CharField(
        max_length=50,
        required=False,
        label='Contact Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    farm_area = forms.CharField(
        max_length=200,
        required=False,
        label='Farm Location',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    operator_type = forms.CharField(
        required=False,
        initial='bufia',
        widget=forms.HiddenInput()
    )
    service_type = forms.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        required=False,
        label='Service Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    land_length = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Length (meters)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    land_width = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Width (meters)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    area = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label='Land Area (hectares)',
        help_text='From your membership application',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01', 
            'placeholder': 'e.g., 2.5',
            'min': '0.01',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    payment_method = forms.ChoiceField(
        choices=[('online', 'Gcash Payment'), ('face_to_face', 'Over the Counter')],
        required=False,
        label='Payment Method',
        widget=forms.RadioSelect()
    )
    payment_type = forms.ChoiceField(
        choices=[('cash', 'Fixed Rate (Cash)'), ('in_kind', 'Non-cash payment')],
        required=False,
        label='Payment Type',
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date', 'area', 'purpose']
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 2.5', 'min': '0.01'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Any additional notes or special requirements'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Allow pre-selecting a machine from the URL
        machine_id = kwargs.pop('machine_id', None)
        # Get user for autofilling personal details
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        self.is_admin_booking = _is_admin_booking_actor(user)
        self._resolved_booking_user = None
        self.pending_conflicts = Rental.objects.none()
        
        current_machine_id = getattr(self.instance, 'machine_id', None)
        rentable_machines = Machine.objects.exclude(
            machine_type__in=SEPARATE_SERVICE_MACHINE_TYPES
        ).filter(
            ~Q(maintenance_records__status__in=['scheduled', 'in_progress']) | Q(pk=current_machine_id)
        ).distinct().order_by('name')

        self.fields['machine'].queryset = rentable_machines
        
        # If a machine ID was provided, preselect it
        # Store it for later use in clean method
        self._preselected_machine_id = None
        if machine_id:
            try:
                machine = Machine.objects.get(pk=machine_id)
                self.fields['machine'].initial = machine
                self.initial['machine'] = machine.pk
                self._preselected_machine_id = machine_id
                # Make field not required since we'll handle it in clean()
                self.fields['machine'].required = False
            except Machine.DoesNotExist:
                pass

        # Dynamically align payment controls with selected machine setup
        selected_machine = None
        if machine_id:
            selected_machine = Machine.objects.filter(pk=machine_id).first()
        elif self.initial.get('machine'):
            selected_machine = Machine.objects.filter(pk=self.initial.get('machine')).first()
        elif self.data.get('machine'):
            selected_machine = Machine.objects.filter(pk=self.data.get('machine')).first()

        if selected_machine:
            self.initial['payment_type'] = selected_machine.rental_price_type
            self.fields['payment_type'].initial = selected_machine.rental_price_type
            if selected_machine.rental_price_type == 'in_kind':
                self.fields['payment_method'].required = False
                self.fields['payment_method'].choices = []
            else:
                selected_member_for_payment = None
                if self.is_admin_booking:
                    selected_member_for_payment = _resolve_member_user(
                        self.data.get('selected_member_id') or self.initial.get('selected_member_id')
                    )
                method_choices = []
                if selected_machine.allow_online_payment and (not self.is_admin_booking or selected_member_for_payment):
                    method_choices.append(('online', 'Gcash Payment'))
                if selected_machine.allow_face_to_face_payment:
                    method_choices.append(('face_to_face', 'Over the Counter'))
                self.fields['payment_method'].choices = method_choices or [('face_to_face', 'Over the Counter')]

        self.fields['operator_type'].initial = 'bufia'
        self.initial['operator_type'] = 'bufia'

        # Enforce advance booking for portal users at the UI level.
        today = timezone.localdate()
        min_start = today if self.is_admin_booking else (today + timezone.timedelta(days=1))
        min_start_str = min_start.strftime('%Y-%m-%d')
        self.fields['start_date'].widget.attrs.setdefault('min', min_start_str)
        self.fields['end_date'].widget.attrs.setdefault('min', min_start_str)

        if self.instance.pk and self.instance.purpose and not self.is_bound:
            service_line_prefix = 'Service Type: '
            for line in self.instance.purpose.splitlines():
                if line.startswith(service_line_prefix):
                    existing_label = line[len(service_line_prefix):].strip()
                    existing_value = next(
                        (value for value, label in self.SERVICE_TYPE_CHOICES if label == existing_label),
                        ''
                    )
                    if existing_value:
                        self.initial['service_type'] = existing_value
                        break

        if selected_machine and not self.is_bound and not self.initial.get('service_type'):
            default_service = self.MACHINE_SERVICE_DEFAULTS.get(selected_machine.machine_type)
            if default_service:
                self.initial['service_type'] = default_service
        
        # Autofill user details from membership application
        if user and hasattr(user, 'membership_application'):
            membership = user.membership_application
            
            # Autofill requester name
            if not self.initial.get('requester_name'):
                full_name = user.get_full_name()
                if full_name:
                    self.initial['requester_name'] = full_name
                else:
                    self.initial['requester_name'] = user.username
            
            # Autofill farm location from bufia_farm_location or farm_location
            if not self.initial.get('farm_area'):
                farm_location = _membership_farm_location(user)
                if farm_location:
                    self.initial['farm_area'] = farm_location
            
            # Autofill land area from farm_size
            if not self.initial.get('area') and membership.farm_size:
                self.initial['area'] = membership.farm_size

        if self.is_admin_booking:
            self.fields['requester_name'].label = 'Farmer / Renter Name'
            self.fields['requester_name'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Type a member name or enter a walk-in renter',
                'autocomplete': 'off',
                'data-member-autocomplete': 'name',
            })
            self.fields['requester_contact_number'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Contact number',
            })
            self.fields['farm_area'].label = 'Address / Farm Location'
            self.fields['farm_area'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Address or farm location',
            })
            self.fields['area'].widget.attrs.update({
                'readonly': False,
                'style': '',
            })
            self.fields['area'].help_text = 'Admin can override or enter the renter land area in hectares.'
            self.fields['requester_name'].required = True
        else:
            self.fields['selected_member_id'].widget = forms.HiddenInput()

        if self.instance.pk and not self.is_bound:
            self.initial.setdefault('requester_name', self.instance.customer_display_name)
            self.initial.setdefault('requester_contact_number', self.instance.customer_display_contact_number)
            self.initial.setdefault('farm_area', self.instance.customer_display_address or self.instance.field_location or '')
    
    def clean(self):
        """Enhanced validation with comprehensive checks"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        machine = cleaned_data.get('machine')
        cleaned_data['operator_type'] = 'bufia'
        selected_member = None
        if self.is_admin_booking:
            selected_member = _resolve_member_user(cleaned_data.get('selected_member_id'))
        
        # Handle preselected machine from URL
        if not machine and hasattr(self, '_preselected_machine_id') and self._preselected_machine_id:
            try:
                machine = Machine.objects.get(pk=self._preselected_machine_id)
                cleaned_data['machine'] = machine
            except Machine.DoesNotExist:
                raise ValidationError('Selected machine does not exist.')
        
        # Handle case where machine field is disabled in form
        if not machine and 'machine' in self.initial:
            try:
                machine = Machine.objects.get(pk=self.initial['machine'])
                cleaned_data['machine'] = machine
            except Machine.DoesNotExist:
                raise ValidationError('Selected machine does not exist.')
        
        if not machine:
            raise ValidationError('Please select a machine.')

        if machine.machine_type in SEPARATE_SERVICE_MACHINE_TYPES:
            if machine.is_dryer_service():
                raise ValidationError(
                    'Dryer services use a separate dryer rental process. Please use the Dryer Rental module.'
                )
            raise ValidationError(
                'Rice mill uses a separate appointment process. Please use the Rice Mill Appointment module.'
            )

        # Source-of-truth: payment mode comes from machine setup.
        cleaned_data['payment_type'] = machine.rental_price_type
        
        if start_date and end_date and machine:
            today = timezone.now().date()

            if machine.get_operational_status() == 'maintenance':
                raise ValidationError(_maintenance_block_message(machine))
            
            # Validation 1: End date must be after or equal to start date
            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })
            
            # Validation 2: Start date cannot be in the past
            if start_date < today:
                raise ValidationError({
                    'start_date': 'Start date cannot be in the past.'
                })
            
            # Validation 3: Maximum rental period (30 days)
            rental_days = (end_date - start_date).days + 1
            if rental_days > 30:
                raise ValidationError(
                    f'Rental period cannot exceed 30 days. You selected {rental_days} days.'
                )
            
            # Validation 4: Minimum advance booking (1 day) for portal users
            days_in_advance = (start_date - today).days
            if self.is_admin_booking and selected_member and days_in_advance < 1:
                raise ValidationError({
                    'start_date': 'Same-day rentals are for walk-in bookings only. Members must book at least 1 day in advance.'
                })
            if not self.is_admin_booking and days_in_advance < 1:
                raise ValidationError({
                    'start_date': 'Bookings must be made at least 1 day in advance.'
                })
            
            # Validation 5: Check if user already has an active rental for this machine
            booking_user = selected_member if self.is_admin_booking else (
                self._resolved_booking_user if hasattr(self, '_resolved_booking_user') and self._resolved_booking_user else self.user
            )
            if booking_user:
                exclude_id = self.instance.pk if self.instance.pk else None
                existing_rental = Rental.objects.filter(
                    user=booking_user,
                    machine=machine,
                    status__in=['pending', 'approved', 'assigned']
                ).exclude(
                    pk=exclude_id
                ).exclude(
                    workflow_state__in=['cancelled', 'completed']
                ).exclude(
                    # Exclude rentals that don't overlap with the requested dates
                    Q(end_date__lt=start_date) | Q(start_date__gt=end_date)
                ).first()
                
                if existing_rental:
                    raise ValidationError(
                        f'You already have an active rental for {machine.name} '
                        f'(from {existing_rental.start_date} to {existing_rental.end_date}, '
                        f'Status: {existing_rental.get_status_display()}) that overlaps with your requested dates. '
                        f'Please choose different dates or wait until your current rental is completed.'
                    )
            
            # Validation 6: Check machine availability using the model method
            exclude_id = self.instance.pk if self.instance.pk else None
            is_available, conflicts = Rental.check_availability(
                machine=machine,
                start_date=start_date,
                end_date=end_date,
                exclude_rental_id=exclude_id
            )
            
            if not is_available:
                conflict = conflicts.first()
                error_msg = (
                    f'This machine is already booked from {conflict.start_date} '
                    f'to {conflict.end_date} (Status: {conflict.get_status_display()}). '
                    f'Please choose different dates.'
                )
                raise ValidationError(error_msg)

            self.pending_conflicts = Rental.get_pending_overlaps(
                machine=machine,
                start_date=start_date,
                end_date=end_date,
                exclude_rental_id=exclude_id,
            )
            
            # Validation 7: Check maintenance schedule
            from machines.models import Maintenance
            maintenance_conflicts = Maintenance.objects.filter(
                machine=machine,
                status__in=['scheduled', 'in_progress'],
                start_date__date__lte=end_date,
                end_date__date__gte=start_date
            )
            
            if maintenance_conflicts.exists():
                maintenance = maintenance_conflicts.first()
                raise ValidationError(
                    f'Machine is scheduled for maintenance from '
                    f'{maintenance.start_date.date()} to '
                    f'{maintenance.end_date.date() if maintenance.end_date else "TBD"}. '
                    f'Please choose different dates.'
                )

        payment_type = cleaned_data.get('payment_type')
        payment_method = cleaned_data.get('payment_method')
        if payment_type == 'in_kind':
            cleaned_data['payment_method'] = None
        elif self.is_admin_booking and not selected_member:
            if machine and not machine.allow_face_to_face_payment:
                raise ValidationError({
                    'payment_method': 'Walk-in rentals must use over-the-counter payment, but this machine is not configured for over-the-counter payment.'
                })
            if payment_method == 'online':
                raise ValidationError({
                    'payment_method': 'Walk-in rentals must use over-the-counter payment.'
                })
            cleaned_data['payment_method'] = 'face_to_face'
            payment_method = 'face_to_face'
        if payment_type == 'cash' and not payment_method:
            raise ValidationError({'payment_method': 'Please select a payment method for cash rentals.'})
        if payment_type == 'cash' and payment_method == 'online' and machine:
            projected_amount = Rental(
                machine=machine,
                start_date=cleaned_data.get('start_date'),
                end_date=cleaned_data.get('end_date'),
                area=cleaned_data.get('area'),
                payment_type='cash',
            ).calculate_payment_amount()
            if projected_amount > ONLINE_PAYMENT_MAX_AMOUNT_PHP:
                raise ValidationError({
                    'payment_method': (
                        f'Online payment is limited to PHP {ONLINE_PAYMENT_MAX_AMOUNT_PHP:,.2f} per transaction. '
                        f'Current total is PHP {projected_amount:,.2f}. Please choose Over-the-Counter payment.'
                    )
                })

        if self.is_admin_booking:
            requester_name = (cleaned_data.get('requester_name') or '').strip()
            requester_contact_number = (cleaned_data.get('requester_contact_number') or '').strip()
            farm_area = (cleaned_data.get('farm_area') or '').strip()
            if selected_member:
                cleaned_data['requester_name'] = _display_name_for_user(selected_member)
                cleaned_data['requester_contact_number'] = selected_member.phone_number or ''
                cleaned_data['farm_area'] = _membership_farm_location(selected_member) or selected_member.address or farm_area
                cleaned_data['area'] = cleaned_data.get('area') or _membership_farm_size(selected_member)
                self._resolved_booking_user = selected_member
            else:
                if not requester_name:
                    raise ValidationError({'requester_name': 'Enter a renter name or select an existing member.'})
                self._resolved_booking_user = _get_or_create_system_booking_user()
                cleaned_data['requester_contact_number'] = requester_contact_number
                cleaned_data['farm_area'] = farm_area
        else:
            self._resolved_booking_user = self.user

        if not cleaned_data.get('service_type'):
            raise ValidationError({'service_type': 'Please select a service type before continuing.'})
        
        return cleaned_data

    def apply_booking_identity(self, rental):
        booking_user = self._resolved_booking_user or self.user or getattr(rental, 'user', None)
        if booking_user is not None:
            rental.user = booking_user
        rental.customer_name = (self.cleaned_data.get('requester_name') or '').strip()
        rental.customer_contact_number = (self.cleaned_data.get('requester_contact_number') or '').strip()
        rental.customer_address = (self.cleaned_data.get('farm_area') or '').strip()
        if rental.customer_address:
            rental.field_location = rental.customer_address

    def save(self, commit=True):
        """Save the rental and append additional details to purpose field"""
        rental = super().save(commit=False)
        self.apply_booking_identity(rental)
        
        # Build detailed purpose from additional fields
        details = []
        
        requester_name = self.cleaned_data.get('requester_name')
        if requester_name:
            details.append(f"Requester: {requester_name}")
        
        farm_area = self.cleaned_data.get('farm_area')
        if farm_area:
            details.append(f"Farm Area: {farm_area}")
        
        details.append("Operator: BUFIA Operator")

        service_type = self.cleaned_data.get('service_type')
        if service_type:
            service_label = dict(self.SERVICE_TYPE_CHOICES).get(service_type, service_type)
            details.append(f"Service Type: {service_label}")
        
        area = self.cleaned_data.get('area')
        if area:
            details.append(f"Land Area: {area} hectares")
        
        land_length = self.cleaned_data.get('land_length')
        land_width = self.cleaned_data.get('land_width')
        if land_length and land_width:
            details.append(f"Dimensions: {land_length}m x {land_width}m")
        
        # Combine with existing purpose
        if details:
            detail_text = "\n".join(details)
            if rental.purpose:
                rental.purpose = f"{detail_text}\n\nAdditional Notes:\n{rental.purpose}"
            else:
                rental.purpose = detail_text
        
        # Set payment method if provided
        payment_method = self.cleaned_data.get('payment_method')
        if payment_method:
            rental.payment_method = payment_method
        payment_type = self.cleaned_data.get('payment_type')
        if payment_type:
            rental.payment_type = payment_type
        if rental.payment_type == 'in_kind':
            rental.payment_status = 'to_be_determined'
            rental.settlement_status = 'to_be_determined'
            rental.payment_method = None
            rental.settlement_type = 'after_harvest'
            rental.payment_verified = False
        elif rental.payment_type == 'cash' and not rental.payment_status:
            rental.payment_status = 'pending'

        if commit:
            rental.save()
        
        return rental


class RentalPackageRequestForm(forms.ModelForm):
    MIN_SELECTED_SERVICES = 2
    MAX_SELECTED_SERVICES = 5
    PACKAGE_SERVICE_FIELDS = [
        ('include_tractor', 'Tractor / Plowing', 'tractor'),
        ('include_rotavator', 'Rotavator / Land Cultivation', 'rotavator'),
        ('include_planter', 'Planter', 'planter'),
        ('include_harvester', 'Harvester', 'harvester'),
        ('include_thresher', 'Thresher', 'thresher'),
    ]
    SERVICE_CARD_COPY = {
        'tractor': 'Preferred starting step for land preparation.',
        'rotavator': 'Follow-up cultivation after plowing.',
        'planter': 'Optional planting step if needed.',
        'harvester': 'Usually scheduled later as a tentative harvest step.',
        'thresher': 'Optional post-harvest threshing step.',
    }
    SERVICE_DEFINITIONS = {
        'tractor': {
            'service_name': 'Tractor / Plowing',
            'machine_type_required': 'tractor',
            'sequence_order': 1,
            'offset_days': 0,
            'tentative': False,
        },
        'rotavator': {
            'service_name': 'Rotavator / Land Cultivation',
            'machine_type_required': 'tractor',
            'sequence_order': 2,
            'offset_days': 1,
            'tentative': False,
        },
        'planter': {
            'service_name': 'Planter',
            'machine_type_required': 'transplanter',
            'sequence_order': 3,
            'offset_days': 2,
            'tentative': False,
        },
        'harvester': {
            'service_name': 'Harvester',
            'machine_type_required': 'harvester',
            'sequence_order': 4,
            'offset_days': 90,
            'tentative': True,
        },
        'thresher': {
            'service_name': 'Thresher',
            'machine_type_required': 'thresher',
            'sequence_order': 5,
            'offset_days': 91,
            'tentative': True,
        },
    }
    selected_member_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    farmer_name = forms.CharField(
        max_length=200,
        required=False,
        label='Farmer Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;',
        }),
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        label='Farm Location',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;',
        }),
    )
    area = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label='Land Area (hectares)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;',
        }),
    )
    include_tractor = forms.BooleanField(required=False, label='Tractor / Plowing')
    include_rotavator = forms.BooleanField(required=False, label='Rotavator / Land Cultivation')
    include_planter = forms.BooleanField(required=False, label='Planter')
    include_harvester = forms.BooleanField(required=False, label='Harvester')
    include_thresher = forms.BooleanField(required=False, label='Thresher')

    class Meta:
        model = RentalPackage
        fields = [
            'package_name',
            'farmer_name',
            'location',
            'area',
            'preferred_start_date',
            'is_urgent',
            'payment_preference',
            'notes',
        ]
        widgets = {
            'package_name': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_preference': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'package_name': 'Package Name',
            'preferred_start_date': 'Preferred Start Date',
            'is_urgent': 'Mark as urgent',
            'payment_preference': 'Payment Preference',
            'notes': 'Additional Notes',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.is_admin_booking = _is_admin_booking_actor(self.user)
        self._resolved_booking_user = self.user
        super().__init__(*args, **kwargs)
        self.fields['package_name'].initial = self.initial.get('package_name') or 'Whole Farming Service Package'
        self.fields['preferred_start_date'].widget.attrs['min'] = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.fields['payment_preference'].help_text = 'Used for cash package items after admin scheduling is confirmed.'
        self.fields['area'].help_text = 'Used for package estimates and service scheduling.'
        self.selected_service_machines = {}

        for _include_field_name, label, service_code in self.PACKAGE_SERVICE_FIELDS:
            definition = self.SERVICE_DEFINITIONS[service_code]
            machine_requirement = definition['machine_type_required']
            machine_group_label = Machine.get_machine_category_label(machine_requirement)
            choice_field_name = self.get_machine_field_name(service_code)
            queryset = Machine.objects.exclude(
                status='maintenance',
            )
            if Machine.is_machine_category_value(machine_requirement):
                queryset = queryset.filter(machine_category=machine_requirement)
            else:
                queryset = queryset.filter(machine_type=machine_requirement)
            queryset = queryset.order_by('name', 'pk')
            self.fields[choice_field_name] = MachineSummaryChoiceField(
                queryset=queryset,
                required=False,
                label=f'Preferred {machine_group_label} Type',
                empty_label=f'Select {machine_group_label}',
                widget=forms.Select(attrs={
                    'class': 'form-select',
                    'data-package-machine-select': service_code,
                }),
                help_text=f'Required when this service is selected. Choose the {machine_group_label.lower()} to reserve for this package step.',
            )

        if self.is_admin_booking:
            self.fields['farmer_name'].label = 'Farmer / Renter Name'
            self.fields['farmer_name'].required = True
            self.fields['farmer_name'].help_text = 'Type a member name to search, or enter a walk-in renter.'
            self.fields['farmer_name'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Type a member name or enter a walk-in renter',
                'autocomplete': 'off',
                'data-member-autocomplete': 'name',
            })
            self.fields['location'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Address or farm location',
            })
            self.fields['area'].widget.attrs.update({
                'readonly': False,
                'style': '',
            })
        elif self.user:
            self.initial['farmer_name'] = _display_name_for_user(self.user)
            self.initial['location'] = _membership_farm_location(self.user)
            membership_area = _membership_farm_size(self.user)
            if membership_area is not None:
                self.initial['area'] = membership_area

    @classmethod
    def get_machine_field_name(cls, service_code):
        return f'{service_code}_machine'

    def get_service_field_groups(self):
        groups = []
        for include_field_name, label, service_code in self.PACKAGE_SERVICE_FIELDS:
            groups.append({
                'service_code': service_code,
                'title': label,
                'description': self.SERVICE_CARD_COPY.get(service_code, ''),
                'machine_requirement_label': Machine.get_machine_category_label(self.SERVICE_DEFINITIONS[service_code]['machine_type_required']),
                'include_field': self[include_field_name],
                'machine_field': self[self.get_machine_field_name(service_code)],
            })
        return groups

    def get_machine_pricing_catalog(self):
        area_value = self.data.get('area') if self.is_bound else (
            self.initial.get('area') or self.fields['area'].initial
        )
        catalog = {}
        for _include_field_name, label, service_code in self.PACKAGE_SERVICE_FIELDS:
            field = self.fields[self.get_machine_field_name(service_code)]
            service_catalog = {}
            for machine in field.queryset:
                preview = machine.get_package_price_preview(area=area_value)
                service_catalog[str(machine.pk)] = {
                    'id': machine.pk,
                    'name': machine.name,
                    'label': label,
                    'machine_type': machine.machine_type,
                    'machine_type_display': machine.get_machine_type_display(),
                    'preview': preview,
                }
            catalog[service_code] = service_catalog
        return catalog

    def clean(self):
        cleaned_data = super().clean()
        selected_services = [
            service_code
            for field_name, _label, service_code in self.PACKAGE_SERVICE_FIELDS
            if cleaned_data.get(field_name)
        ]
        if not selected_services:
            raise ValidationError('Select at least one service for the rental package.')
        if len(selected_services) < self.MIN_SELECTED_SERVICES:
            raise ValidationError(
                f'Choose at least {self.MIN_SELECTED_SERVICES} services for one package request.'
            )
        if len(selected_services) > self.MAX_SELECTED_SERVICES:
            raise ValidationError(
                f'Choose up to {self.MAX_SELECTED_SERVICES} services only for one package request.'
            )

        preferred_start_date = cleaned_data.get('preferred_start_date')
        if preferred_start_date and preferred_start_date <= timezone.localdate():
            raise ValidationError({'preferred_start_date': 'Preferred start date must be at least one day ahead.'})

        if self.is_admin_booking:
            farmer_name = (cleaned_data.get('farmer_name') or '').strip()
            selected_member = _resolve_member_user(cleaned_data.get('selected_member_id'))
            if selected_member:
                cleaned_data['farmer_name'] = _display_name_for_user(selected_member)
                cleaned_data['location'] = _membership_farm_location(selected_member) or selected_member.address or ''
                cleaned_data['area'] = cleaned_data.get('area') or _membership_farm_size(selected_member)
                self._resolved_booking_user = selected_member
            else:
                if not farmer_name:
                    raise ValidationError({'farmer_name': 'Enter a renter name or choose a suggested member.'})
                self._resolved_booking_user = _get_or_create_system_booking_user()
        elif self.user:
            cleaned_data['farmer_name'] = cleaned_data.get('farmer_name') or _display_name_for_user(self.user)
            cleaned_data['location'] = cleaned_data.get('location') or _membership_farm_location(self.user)
            if cleaned_data.get('area') in [None, '']:
                membership_area = _membership_farm_size(self.user)
                if membership_area is not None:
                    cleaned_data['area'] = membership_area

        for _include_field_name, _label, service_code in self.PACKAGE_SERVICE_FIELDS:
            machine_field_name = self.get_machine_field_name(service_code)
            selected_machine = cleaned_data.get(machine_field_name)
            if service_code not in selected_services:
                cleaned_data[machine_field_name] = None
                continue

            required_value = self.SERVICE_DEFINITIONS[service_code]['machine_type_required']
            if not selected_machine:
                self.add_error(
                    machine_field_name,
                    'Select a machine for this service before submitting the package request.',
                )
                continue
            if selected_machine:
                if Machine.is_machine_category_value(required_value):
                    if selected_machine.resolved_machine_category != required_value:
                        self.add_error(machine_field_name, 'The selected machine does not match this service category.')
                elif selected_machine.machine_type != required_value:
                    self.add_error(machine_field_name, 'The selected machine does not match this service type.')
            self.selected_service_machines[service_code] = selected_machine

        self.selected_services = selected_services
        return cleaned_data

    def _estimate_item_defaults(self, definition, package, machine=None):
        if machine is None:
            machine_queryset = Machine.objects.exclude(status='maintenance')
            required_value = definition['machine_type_required']
            if Machine.is_machine_category_value(required_value):
                machine_queryset = machine_queryset.filter(machine_category=required_value)
            else:
                machine_queryset = machine_queryset.filter(machine_type=required_value)
            machine = machine_queryset.order_by('name', 'pk').first()
        pricing_unit = 'day'
        rate = Decimal('0.00')
        quantity = Decimal('1.0000')
        if machine:
            pricing = machine.get_pricing_info()
            pricing_unit = pricing.get('unit') or machine._default_pricing_unit()
            rate = Decimal(str(pricing.get('rate') or '0.00')).quantize(Decimal('0.01'))
            if pricing_unit == 'hectare':
                quantity = Decimal(str(package.area or '0.00')).quantize(Decimal('0.0001'))
            elif pricing_unit in ['day', 'flat']:
                quantity = Decimal('1.0000')
            else:
                quantity = Decimal('0.0000')
        return pricing_unit, rate, quantity

    def save(self, commit=True):
        if not hasattr(self, 'selected_services'):
            self.full_clean()

        package = super().save(commit=False)
        package.user = self._resolved_booking_user or self.user
        package.farmer_name = self.cleaned_data.get('farmer_name') or _display_name_for_user(package.user)
        package.location = self.cleaned_data.get('location') or _membership_farm_location(package.user)
        package.status = 'pending'
        package.payment_status = 'pending'

        if commit:
            with transaction.atomic():
                package.save()
                for service_code in self.selected_services:
                    definition = self.SERVICE_DEFINITIONS[service_code]
                    selected_machine = self.selected_service_machines.get(service_code)
                    suggested_start = package.preferred_start_date + timedelta(days=definition['offset_days'])
                    suggested_end = suggested_start
                    pricing_unit, rate, quantity = self._estimate_item_defaults(definition, package, machine=selected_machine)
                    item_status = 'tentative' if definition['tentative'] else 'requested'
                    RentalPackageItem.objects.create(
                        rental_package=package,
                        machine=selected_machine,
                        service_code=service_code,
                        service_name=definition['service_name'],
                        machine_type_required=definition['machine_type_required'],
                        pricing_unit=pricing_unit,
                        rate=rate,
                        quantity=quantity,
                        suggested_start=suggested_start,
                        suggested_end=suggested_end,
                        scheduled_start=suggested_start if not definition['tentative'] else None,
                        scheduled_end=suggested_end if not definition['tentative'] else None,
                        is_tentative=definition['tentative'],
                        status=item_status,
                        sequence_order=definition['sequence_order'],
                    )
                package.refresh_total_amount(save=True)
        return package


class RentalPackageItemScheduleForm(forms.ModelForm):
    class Meta:
        model = RentalPackageItem
        fields = ['machine', 'quantity', 'scheduled_start', 'scheduled_end', 'is_tentative', 'status', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'scheduled_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'scheduled_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['machine'].queryset = self.instance.get_candidate_machine_queryset()
        self.fields['machine'].required = False
        self.fields['machine'].widget.attrs.update({'class': 'form-select form-select-sm'})
        actionable_statuses = ['requested', 'scheduled']
        status_label_map = dict(RentalPackageItem.ITEM_STATUS_CHOICES)
        current_status = self.instance.status
        posted_status = None
        if self.is_bound:
            posted_status = self.data.get(self.add_prefix('status'))
            if posted_status == 'tentative':
                actionable_statuses.append('tentative')
        if current_status and current_status not in actionable_statuses and current_status != 'tentative':
            actionable_statuses.append(current_status)
        self.fields['status'].choices = [
            (value, status_label_map[value])
            for value in actionable_statuses
            if value in status_label_map
        ]
        if current_status == 'tentative' and not self.is_bound:
            self.initial['status'] = 'requested'
        if current_status in {'completed', 'cancelled'}:
            for field_name in ['machine', 'quantity', 'scheduled_start', 'scheduled_end', 'is_tentative', 'status', 'notes']:
                self.fields[field_name].disabled = True
        min_date = self.instance.rental_package.preferred_start_date.isoformat()
        self.fields['scheduled_start'].widget.attrs['min'] = min_date
        self.fields['scheduled_end'].widget.attrs['min'] = min_date
        self.fields['scheduled_start'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['scheduled_end'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['status'].widget.attrs['class'] = 'form-select form-select-sm'
        self.fields['notes'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['quantity'].widget.attrs['class'] = 'form-control form-control-sm'
        if self.instance.suggested_start and not self.instance.scheduled_start:
            self.initial.setdefault('scheduled_start', self.instance.suggested_start)
        if self.instance.suggested_end and not self.instance.scheduled_end:
            self.initial.setdefault('scheduled_end', self.instance.suggested_end)
        self.fields['quantity'].label = self.instance.quantity_label_display
        self.fields['quantity'].help_text = self.instance.quantity_source_label

        if self.instance.pricing_unit in {'hectare', 'day', 'flat'}:
            self.initial['quantity'] = self.instance.effective_pricing_quantity
            self.fields['quantity'].widget.attrs['readonly'] = 'readonly'
            self.fields['quantity'].widget.attrs['aria-label'] = self.instance.quantity_label_display
        else:
            self.fields['quantity'].widget.attrs['placeholder'] = self.instance.quantity_label_display

    def clean(self):
        cleaned_data = super().clean()
        is_tentative = cleaned_data.get('is_tentative')
        status = cleaned_data.get('status')
        machine = cleaned_data.get('machine')
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        quantity = cleaned_data.get('quantity')

        if scheduled_start and scheduled_end and scheduled_end < scheduled_start:
            raise ValidationError({'scheduled_end': 'Scheduled end date cannot be before the start date.'})

        if is_tentative:
            cleaned_data['status'] = 'tentative'
        elif status == 'tentative' and machine and scheduled_start and scheduled_end:
            cleaned_data['status'] = 'scheduled'
        status = cleaned_data.get('status')

        if status in ['scheduled', 'in_progress', 'completed'] and not is_tentative:
            if not machine:
                raise ValidationError({'machine': 'Assign a machine before marking this service as scheduled.'})
            if not scheduled_start or not scheduled_end:
                raise ValidationError('Scheduled start and end dates are required for confirmed package items.')

            is_available, conflicts = Rental.check_availability_for_approval(
                machine,
                scheduled_start,
                scheduled_end,
                exclude_rental_id=self.instance.linked_rental_id,
            )
            if not is_available:
                conflict = conflicts.first()
                raise ValidationError({
                    'scheduled_start': (
                        f'{machine.name} is already reserved from '
                        f'{conflict.start_date} to {conflict.end_date}.'
                    )
                })

            maintenance_conflict = Maintenance.objects.filter(
                machine=machine,
                status__in=['scheduled', 'in_progress'],
                start_date__date__lte=scheduled_end,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__date__gte=scheduled_start)
            ).first()
            if maintenance_conflict:
                raise ValidationError({
                    'scheduled_start': (
                        f'{machine.name} has maintenance scheduled during this period.'
                    )
                })

        if quantity in [None, '']:
            cleaned_data['quantity'] = self.instance.compute_default_quantity()
        return cleaned_data


RentalPackageItemScheduleFormSet = inlineformset_factory(
    RentalPackage,
    RentalPackageItem,
    form=RentalPackageItemScheduleForm,
    extra=0,
    can_delete=False,
)


class AdminRentalForm(forms.ModelForm):
    """Admin form for creating rentals on behalf of users"""
    selected_member_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    renter_name = forms.CharField(
        max_length=200,
        label='Renter Name',
        required=True,
        help_text='Type a member name to search, or enter a walk-in renter.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter renter name', 'autocomplete': 'off', 'data-member-autocomplete': 'name'})
    )
    renter_contact_number = forms.CharField(
        max_length=50,
        required=True,
        label='Contact Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'})
    )
    renter_address = forms.CharField(
        required=True,
        label='Address / Farm Location',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address or farm location'})
    )
    
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date', 'area', 'purpose', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_admin_booking = True  # Mark this as an admin booking
        self._resolved_booking_user = None
        current_machine_id = getattr(self.instance, 'machine_id', None)
        self.fields['machine'].queryset = Machine.objects.exclude(
            machine_type__in=SEPARATE_SERVICE_MACHINE_TYPES
        ).filter(
            ~Q(maintenance_records__status__in=['scheduled', 'in_progress']) | Q(pk=current_machine_id)
        ).distinct().order_by('name')
        
        # Make area field required
        self.fields['area'].required = True
        
        # Set initial status to approved for admin-created rentals
        if not self.instance.pk:
            self.fields['status'].initial = 'approved'
        elif self.instance.pk and self.instance.user:
            self.fields['renter_name'].initial = self.instance.customer_display_name
            self.fields['renter_contact_number'].initial = self.instance.customer_display_contact_number
            self.fields['renter_address'].initial = self.instance.customer_display_address

    def clean(self):
        cleaned_data = super().clean()
        renter_name = (cleaned_data.get('renter_name') or '').strip()
        selected_member = _resolve_member_user(cleaned_data.get('selected_member_id'))
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        machine = cleaned_data.get('machine')

        if start_date and end_date and machine:
            today = timezone.localdate()

            if machine.get_operational_status() == 'maintenance':
                raise ValidationError(_maintenance_block_message(machine))

            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })

            # Allow same-day rentals for walk-ins, but not past dates
            if start_date < today:
                raise ValidationError({
                    'start_date': 'Start date cannot be in the past.'
                })

            rental_days = (end_date - start_date).days + 1
            if rental_days > 30:
                raise ValidationError(
                    f'Rental period cannot exceed 30 days. You selected {rental_days} days.'
                )

            # Same-day rentals are allowed for walk-ins (no selected_member)
            # Members must book at least 1 day in advance
            if selected_member and start_date == today:
                raise ValidationError({
                    'start_date': 'Same-day rentals are for walk-in bookings only. Members must book at least 1 day in advance.'
                })

            exclude_id = self.instance.pk if self.instance.pk else None
            is_available, conflicts = Rental.check_availability(
                machine=machine,
                start_date=start_date,
                end_date=end_date,
                exclude_rental_id=exclude_id
            )
            if not is_available:
                conflict = conflicts.first()
                raise ValidationError(
                    f'This machine is already booked from {conflict.start_date} '
                    f'to {conflict.end_date} (Status: {conflict.get_status_display()}). '
                    f'Please choose different dates.'
                )

            maintenance_conflicts = Maintenance.objects.filter(
                machine=machine,
                status__in=['scheduled', 'in_progress'],
                start_date__date__lte=end_date,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__date__gte=start_date)
            )
            if maintenance_conflicts.exists():
                maintenance = maintenance_conflicts.first()
                raise ValidationError(
                    f'Machine is scheduled for maintenance from '
                    f'{maintenance.start_date.date()} to '
                    f'{maintenance.end_date.date() if maintenance.end_date else "TBD"}. '
                    f'Please choose different dates.'
                )

        if selected_member:
            cleaned_data['renter_name'] = _display_name_for_user(selected_member)
            cleaned_data['renter_contact_number'] = selected_member.phone_number or ''
            cleaned_data['renter_address'] = _membership_farm_location(selected_member) or selected_member.address or ''
            cleaned_data['area'] = cleaned_data.get('area') or _membership_farm_size(selected_member)
            self._resolved_booking_user = selected_member
        else:
            if not renter_name:
                raise ValidationError({'renter_name': 'Enter a renter name or choose a suggested member.'})
            self._resolved_booking_user = _get_or_create_system_booking_user()
        
        # Validate required fields for all bookings (member or walk-in)
        if not cleaned_data.get('renter_contact_number'):
            raise ValidationError({'renter_contact_number': 'Contact number is required.'})
        if not cleaned_data.get('renter_address'):
            raise ValidationError({'renter_address': 'Address/Farm location is required.'})
        if not cleaned_data.get('area'):
            raise ValidationError({'area': 'Land area is required.'})
        
        return cleaned_data

    def apply_booking_identity(self, rental):
        rental.user = self._resolved_booking_user or rental.user
        rental.customer_name = (self.cleaned_data.get('renter_name') or '').strip()
        rental.customer_contact_number = (self.cleaned_data.get('renter_contact_number') or '').strip()
        rental.customer_address = (self.cleaned_data.get('renter_address') or '').strip()
        if rental.customer_address:
            rental.field_location = rental.customer_address
        if rental.payment_type != 'in_kind':
            rental.payment_type = 'cash'
            rental.payment_method = 'face_to_face'
            rental.payment_status = 'pending'

class MaintenanceForm(forms.ModelForm):
    technician_name = forms.CharField(max_length=100, required=False, help_text="Enter technician name")
    
    class Meta:
        model = Maintenance
        fields = [
            'machine', 'maintenance_type', 'description',
            'start_date', 'end_date',
            'technician_name', 'status'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'description': 'Reason / Initial Assessment',
            'start_date': 'Scheduled Date',
            'end_date': 'Target Completion Date',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['technician_name'].initial = self.instance.display_technician_name

        if 'technician' in self.fields:
            del self.fields['technician']

        if self.instance and self.instance.pk and self.instance.status == 'completed':
            self.fields['status'].choices = Maintenance.STATUS_CHOICES
            self.fields['status'].disabled = True
        else:
            self.fields['status'].choices = [
                choice for choice in Maintenance.STATUS_CHOICES if choice[0] != 'completed'
            ]
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        status = cleaned_data.get('status')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')

        if status == 'completed' and not self.fields['status'].disabled:
            raise ValidationError('Use Finish Maintenance to complete this record.')
        
        return cleaned_data
        
    def save(self, commit=True):
        maintenance = super().save(commit=False)
        maintenance.technician = None
        maintenance.technician_name = (self.cleaned_data.get('technician_name') or '').strip()

        if commit:
            maintenance.save()
            
        return maintenance


class MaintenanceCompletionForm(forms.ModelForm):
    technician_name = forms.CharField(max_length=100, required=True, help_text="Enter technician name")
    labor_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        initial=Decimal('0.00'),
    )
    other_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        initial=Decimal('0.00'),
    )

    class Meta:
        model = Maintenance
        fields = [
            'repair_summary',
            'no_parts_replaced',
            'labor_cost',
            'other_cost',
            'technician_name',
            'completion_notes',
            'actual_completion_date',
        ]
        widgets = {
            'repair_summary': forms.Textarea(attrs={'rows': 4}),
            'completion_notes': forms.Textarea(attrs={'rows': 4}),
            'actual_completion_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'repair_summary': 'Repair Summary',
            'no_parts_replaced': 'No parts replaced',
            'labor_cost': 'Labor Cost',
            'other_cost': 'Other Cost',
            'technician_name': 'Technician Name',
            'completion_notes': 'Completion Notes',
            'actual_completion_date': 'Actual Completion Date',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['repair_summary'].required = True
        self.fields['actual_completion_date'].required = True

        if self.instance and self.instance.pk:
            self.fields['technician_name'].initial = self.instance.display_technician_name
            self.fields['actual_completion_date'].initial = (
                self.instance.actual_completion_date or timezone.localtime(timezone.now())
            )

        for cost_field in ('labor_cost', 'other_cost'):
            self.fields[cost_field].empty_value = Decimal('0.00')

    def clean(self):
        cleaned_data = super().clean()

        labor_cost = cleaned_data.get('labor_cost')
        other_cost = cleaned_data.get('other_cost')
        technician_name = (cleaned_data.get('technician_name') or '').strip()

        cleaned_data['labor_cost'] = labor_cost if labor_cost is not None else Decimal('0.00')
        cleaned_data['other_cost'] = other_cost if other_cost is not None else Decimal('0.00')
        cleaned_data['technician_name'] = technician_name

        if not technician_name:
            self.add_error('technician_name', 'Technician name is required.')

        return cleaned_data

    def save(self, commit=True):
        maintenance = super().save(commit=False)
        maintenance.status = 'completed'
        maintenance.technician = None
        maintenance.technician_name = self.cleaned_data.get('technician_name', '')
        maintenance.labor_cost = self.cleaned_data.get('labor_cost', Decimal('0.00'))
        maintenance.other_cost = self.cleaned_data.get('other_cost', Decimal('0.00'))

        if commit:
            maintenance.save()

        return maintenance


class MaintenancePartUsedForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, required=False)
    unit_price = forms.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'), required=False)

    class Meta:
        model = MaintenancePartUsed
        fields = ['part_name', 'quantity', 'unit_price', 'subtotal']
        widgets = {
            'part_name': forms.TextInput(attrs={'placeholder': 'Part name', 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'subtotal': forms.NumberInput(attrs={'readonly': 'readonly', 'step': '0.01', 'class': 'form-control'}),
        }
        labels = {
            'part_name': 'Part Name',
            'unit_price': 'Unit Price',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['part_name'].required = False
        self.fields['subtotal'].required = False

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('DELETE'):
            return cleaned_data

        part_name = (cleaned_data.get('part_name') or '').strip()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        has_values = bool(part_name or quantity or unit_price is not None)

        if not has_values:
            cleaned_data['part_name'] = ''
            cleaned_data['subtotal'] = Decimal('0.00')
            return cleaned_data

        if not part_name:
            self.add_error('part_name', 'Part name is required.')
        if quantity in (None, ''):
            self.add_error('quantity', 'Quantity is required.')
        if unit_price is None:
            self.add_error('unit_price', 'Unit price is required.')

        if self.errors:
            return cleaned_data

        cleaned_data['part_name'] = part_name
        cleaned_data['subtotal'] = Decimal(quantity) * unit_price
        return cleaned_data


MaintenancePartFormSet = inlineformset_factory(
    Maintenance,
    MaintenancePartUsed,
    form=MaintenancePartUsedForm,
    extra=1,
    can_delete=True,
)

class PriceHistoryForm(forms.ModelForm):
    class Meta:
        model = PriceHistory
        fields = ['price', 'start_date']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        
        if start_date and start_date < timezone.now():
            raise forms.ValidationError("Start date cannot be in the past")
        
        return cleaned_data

class RiceMillAppointmentForm(forms.ModelForm):
    """Form for creating and updating rice mill appointments"""
    
    # Add autofill fields
    selected_member_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    farmer_name = forms.CharField(
        max_length=200,
        required=False,
        label='Your Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    farmer_contact_number = forms.CharField(
        max_length=50,
        required=False,
        label='Contact Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    farm_location = forms.CharField(
        max_length=200,
        required=False,
        label='Farm Location',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f0f9f4; cursor: not-allowed;'
        })
    )
    
    # Add a display field for showing "Rice Mill" text
    machine_display = forms.CharField(
        required=False,
        initial='Rice Mill',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'value': 'Rice Mill',
            'readonly': 'readonly',
            'style': 'background-color: #f8f9fa; cursor: not-allowed;'
        })
    )

    booking_source = forms.ChoiceField(
        choices=RiceMillAppointment.BOOKING_SOURCE_CHOICES,
        required=False,
        label='Milling Source',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = RiceMillAppointment
        fields = ['machine', 'booking_source', 'appointment_date', 'sacks', 'payment_method', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'machine': forms.HiddenInput(),  # Always hide the machine field
        }

    # Use workflow-compatible values while keeping user-friendly labels.
    payment_method = forms.ChoiceField(
        choices=[('face_to_face', 'Over the Counter')],
        required=False,
        label='Payment Method',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        # Pop machine_id and user
        machine_id = kwargs.pop('machine_id', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        self.is_admin_booking = _is_admin_booking_actor(user)
        self._resolved_booking_user = None
        
        # Make machine field not required since it will be auto-selected
        self.fields['machine'].required = False
        
        # Filter machine choices to only rice mills
        rice_mills = Machine.objects.filter(machine_type='rice_mill', status='available')
        if not rice_mills.exists():
            rice_mills = Machine.objects.filter(machine_type='rice_mill')
        if not rice_mills.exists():
            from .views import _ensure_default_rice_mill
            _ensure_default_rice_mill()
            rice_mills = Machine.objects.filter(machine_type='rice_mill', status='available')
            if not rice_mills.exists():
                rice_mills = Machine.objects.filter(machine_type='rice_mill')
        self.fields['machine'].queryset = rice_mills
        
        # Auto-select the first rice mill or the specified one
        if machine_id:
            try:
                machine = Machine.objects.get(pk=machine_id, machine_type='rice_mill')
                self.fields['machine'].initial = machine
            except Machine.DoesNotExist:
                if rice_mills.exists():
                    self.fields['machine'].initial = rice_mills.first()
        elif rice_mills.exists():
            self.fields['machine'].initial = rice_mills.first()
        
        self.fields['payment_method'].choices = [('face_to_face', 'Over the Counter')]
        # Autofill user details from membership application
        if user and hasattr(user, 'membership_application'):
            membership = user.membership_application
            
            # Autofill farmer name
            if not self.initial.get('farmer_name'):
                full_name = user.get_full_name()
                if full_name:
                    self.initial['farmer_name'] = full_name
                else:
                    self.initial['farmer_name'] = user.username
            
            # Autofill farm location
            if not self.initial.get('farm_location'):
                farm_location = _membership_farm_location(user)
                if farm_location:
                    self.initial['farm_location'] = farm_location
            if not self.initial.get('farmer_contact_number'):
                self.initial['farmer_contact_number'] = user.phone_number

        if self.is_admin_booking:
            self.fields['booking_source'].required = False
            self.fields['booking_source'].initial = (
                self.initial.get('booking_source')
                or getattr(self.instance, 'booking_source', None)
                or RiceMillAppointment.BOOKING_SOURCE_MEMBER
            )
            self.fields['farmer_name'].label = 'Farmer / Renter Name'
            self.fields['farmer_name'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Type a member name or enter a walk-in renter',
                'autocomplete': 'off',
                'data-member-autocomplete': 'name',
            })
            self.fields['farmer_contact_number'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Contact number',
            })
            self.fields['farm_location'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Address or farm location',
            })
            self.fields['farmer_name'].required = True

        if self.instance.pk and not self.is_bound:
            self.initial.setdefault('farmer_name', self.instance.customer_display_name)
            self.initial.setdefault('farmer_contact_number', self.instance.customer_display_contact_number)
            self.initial.setdefault('farm_location', self.instance.customer_display_address)
            self.initial.setdefault('booking_source', self.instance.booking_source)
            if (
                self.instance.booking_source == RiceMillAppointment.BOOKING_SOURCE_MEMBER
                and self.instance.user_id
                and self.instance.user.is_active
                and self.instance.user.is_verified
            ):
                self.initial.setdefault('selected_member_id', self.instance.user_id)
        
        # Set the minimum date to today
        self.fields['appointment_date'].widget.attrs['min'] = timezone.now().date().isoformat()
        
        # Add Bootstrap classes and ensure fields are interactive
        self.fields['appointment_date'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'dd/mm/yyyy',
            'required': 'required'
        })
        self.fields['payment_method'].widget.attrs.update({
            'class': 'form-select',
            'data-payment-method-select': 'true',
        })
        self.fields['booking_source'].widget.attrs.update({
            'class': 'form-select',
            'data-booking-source-select': 'true',
        })
        self.fields['sacks'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter number of sacks',
            'type': 'number',
            'min': '1',
            'step': '1',
            'required': 'required'
        })
        self.fields['notes'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Any special instructions or information (optional)',
            'rows': '3'
        })

        if self.is_admin_booking:
            self.fields['payment_method'].required = True
            self.fields['payment_method'].initial = self.initial.get('payment_method') or getattr(self.instance, 'payment_method', None) or 'face_to_face'
            self.fields['payment_method'].help_text = 'Rice mill bookings use over-the-counter payment.'
            self.fields['booking_source'].help_text = 'Choose Member Milling for verified members, Non-member Milling for walk-ins, or BUFIA Rice Share for internal harvest-share milling.'
        else:
            self.fields['payment_method'].required = False
            self.fields['payment_method'].initial = self.initial.get('payment_method') or getattr(self.instance, 'payment_method', None) or 'face_to_face'
            self.fields['payment_method'].help_text = 'Rice mill bookings are paid over the counter after BUFIA finalizes the processed weight.'
            self.fields['booking_source'].widget = forms.HiddenInput()
            self.fields['booking_source'].initial = RiceMillAppointment.BOOKING_SOURCE_MEMBER

        # Set label for machine_display
        self.fields['machine_display'].label = "SELECT RICE MILL"
    
    def clean(self):
        """Validate appointment date and machine availability"""
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        machine = cleaned_data.get('machine')
        sacks = cleaned_data.get('sacks')
        
        # If no machine is selected, auto-select the first available rice mill
        if not machine:
            rice_mills = Machine.objects.filter(machine_type='rice_mill', status='available')
            if rice_mills.exists():
                machine = rice_mills.first()
                cleaned_data['machine'] = machine
            else:
                # If no available rice mills, just use any rice mill
                rice_mills = Machine.objects.filter(machine_type='rice_mill')
                if rice_mills.exists():
                    machine = rice_mills.first()
                    cleaned_data['machine'] = machine
                else:
                    from .views import _ensure_default_rice_mill
                    machine = _ensure_default_rice_mill()
                    cleaned_data['machine'] = machine
        
        # Only validate if all required fields are present
        if appointment_date and machine and sacks:
            # Ensure appointment date is not in the past
            today = timezone.now().date()
            if appointment_date < today:
                raise ValidationError('Appointment date cannot be in the past.')

            # Rice mill can handle multiple appointments per day, so no date conflict check
            # Users can book the same date as other appointments

        if self.is_admin_booking:
            booking_source = cleaned_data.get('booking_source') or RiceMillAppointment.BOOKING_SOURCE_MEMBER
            cleaned_data['booking_source'] = booking_source
            farmer_name = (cleaned_data.get('farmer_name') or '').strip()
            if booking_source == RiceMillAppointment.BOOKING_SOURCE_BUFIA_RICE_SHARE:
                cleaned_data['farmer_name'] = 'BUFIA Rice Share'
                cleaned_data['farmer_contact_number'] = ''
                cleaned_data['farm_location'] = 'BUFIA Harvest Share'
                cleaned_data['payment_method'] = 'face_to_face'
                self._resolved_booking_user = _get_or_create_system_booking_user()
            elif booking_source == RiceMillAppointment.BOOKING_SOURCE_NON_MEMBER:
                if not farmer_name:
                    raise ValidationError({'farmer_name': 'Enter the non-member renter name.'})
                cleaned_data['selected_member_id'] = None
                cleaned_data['payment_method'] = 'face_to_face'
                self._resolved_booking_user = _get_or_create_system_booking_user()
            else:
                selected_member = _resolve_member_user(cleaned_data.get('selected_member_id'))
                if (
                    not selected_member
                    and self.instance.pk
                    and self.instance.booking_source == RiceMillAppointment.BOOKING_SOURCE_MEMBER
                    and self.instance.user_id
                    and self.instance.user.is_active
                    and self.instance.user.is_verified
                ):
                    selected_member = self.instance.user
                if selected_member:
                    cleaned_data['farmer_name'] = _display_name_for_user(selected_member)
                    cleaned_data['farmer_contact_number'] = selected_member.phone_number or ''
                    cleaned_data['farm_location'] = _membership_farm_location(selected_member) or selected_member.address or ''
                    self._resolved_booking_user = selected_member
                    cleaned_data['payment_method'] = 'face_to_face'
                else:
                    raise ValidationError({'farmer_name': 'Choose a verified member for Member Milling bookings.'})
        else:
            self._resolved_booking_user = self.user
            cleaned_data['payment_method'] = 'face_to_face'
            cleaned_data['booking_source'] = RiceMillAppointment.BOOKING_SOURCE_MEMBER

        return cleaned_data 

    def apply_booking_identity(self, appointment):
        booking_user = self._resolved_booking_user or self.user or getattr(appointment, 'user', None)
        if booking_user is not None:
            appointment.user = booking_user
        appointment.booking_source = self.cleaned_data.get('booking_source') or RiceMillAppointment.BOOKING_SOURCE_MEMBER
        appointment.customer_name = (self.cleaned_data.get('farmer_name') or '').strip()
        appointment.customer_contact_number = (self.cleaned_data.get('farmer_contact_number') or '').strip()
        appointment.customer_address = (self.cleaned_data.get('farm_location') or '').strip()
        if self.is_admin_booking:
            appointment.payment_method = self.cleaned_data.get('payment_method') or 'face_to_face'



class DryerRentalForm(forms.ModelForm):
    selected_member_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    rental_type = forms.ChoiceField(
        choices=DryerRental.RENTAL_TYPE_CHOICES,
        initial='until_dried',
        label='Rental Type',
        widget=forms.RadioSelect()
    )
    renter_name = forms.CharField(
        max_length=200,
        required=False,
        label='Your Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'background-color: #f0f9f4; cursor: not-allowed;'})
    )
    renter_contact_number = forms.CharField(
        max_length=50,
        required=False,
        label='Contact Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'background-color: #f0f9f4; cursor: not-allowed;'})
    )
    farm_location = forms.CharField(
        max_length=200,
        required=False,
        label='Farm Location',
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'background-color: #f0f9f4; cursor: not-allowed;'})
    )
    requested_hours = forms.DecimalField(
        required=False,
        min_value=Decimal('0.50'),
        decimal_places=2,
        max_digits=6,
        label='Number of Hours',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5'})
    )
    goods_description = forms.CharField(
        required=False,
        label='Rice Grain Details',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    quantity = forms.CharField(
        required=False,
        label='Rice Grain Quantity',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DryerRental
        fields = [
            'machine', 'rental_type', 'rental_date', 'goods_description',
            'quantity', 'start_time', 'requested_hours', 'notes'
        ]
        widgets = {
            'machine': forms.HiddenInput(),
            'rental_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        machine_id = kwargs.pop('machine_id', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        self.is_admin_booking = _is_admin_booking_actor(user)
        self._resolved_booking_user = None

        all_dryers = Machine.objects.filter(machine_type__in=Machine.DRYER_MACHINE_TYPES).order_by('name', 'pk')
        dryers = all_dryers
        if self.is_admin_booking:
            if self.instance.pk and self.instance.machine_id:
                dryers = all_dryers.filter(Q(status='available') | Q(pk=self.instance.machine_id))
            else:
                dryers = all_dryers.filter(status='available')

        self.fields['machine'].queryset = dryers
        self._selected_machine = None
        self.fields['machine'].required = self.is_admin_booking

        if self.is_admin_booking:
            self.fields['machine'].widget = forms.Select(attrs={'class': 'form-select'})
            self.fields['machine'].label = 'Dryer Unit'
            self.fields['machine'].empty_label = 'Select a dryer'
            self.fields['machine'].widget.choices = self.fields['machine'].choices
        else:
            self.fields['machine'].widget = forms.HiddenInput()

        selection_candidates = []
        if self.is_bound:
            selection_candidates.append(self.data.get('machine'))
        selection_candidates.append(machine_id)
        if self.instance.pk and self.instance.machine_id:
            selection_candidates.append(self.instance.machine_id)
        if dryers.exists():
            selection_candidates.append(dryers.first().pk)

        for candidate in selection_candidates:
            if not candidate:
                continue
            machine = dryers.filter(pk=candidate).first()
            if machine:
                self.fields['machine'].initial = machine.pk
                self.initial['machine'] = machine.pk
                self._selected_machine = machine
                break

        if user and hasattr(user, 'membership_application'):
            membership = user.membership_application
            self.initial['renter_name'] = user.get_full_name() or user.username
            self.initial['renter_contact_number'] = user.phone_number
            self.initial['farm_location'] = _membership_farm_location(user)

        if self.is_admin_booking:
            self.fields['renter_name'].label = 'Farmer / Renter Name'
            self.fields['renter_name'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Type a member name or enter a walk-in renter',
                'autocomplete': 'off',
                'data-member-autocomplete': 'name',
            })
            self.fields['renter_contact_number'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Contact number',
            })
            self.fields['farm_location'].widget.attrs.update({
                'readonly': False,
                'style': '',
                'placeholder': 'Address or farm location',
            })
            self.fields['renter_name'].required = True

        if self.instance.pk and not self.is_bound:
            self.initial.setdefault('renter_name', self.instance.customer_display_name)
            self.initial.setdefault('renter_contact_number', self.instance.customer_display_contact_number)
            self.initial.setdefault('farm_location', self.instance.customer_display_address)
            self.initial.setdefault('rental_type', self.instance.rental_type or self.instance.pricing_type_snapshot or 'until_dried')
            if self.instance.requested_hours is not None:
                self.initial.setdefault('requested_hours', self.instance.requested_hours)
            elif self.instance.start_time and self.instance.end_time:
                self.initial.setdefault('requested_hours', self.instance.duration_hours)
            if self.instance.goods_description:
                self.initial.setdefault('goods_description', self.instance.goods_description)
            if self.instance.quantity:
                self.initial.setdefault('quantity', self.instance.quantity)

        self.fields['rental_date'].widget.attrs.update({'class': 'form-control', 'required': 'required', 'min': timezone.now().date().isoformat()})
        self.fields['start_time'].widget.attrs.update({'class': 'form-control', 'min': '08:00', 'max': '18:00', 'step': '1800'})
        self.fields['goods_description'].widget.attrs.update({'placeholder': 'Describe the rice grain batch to be dried.'})
        self.fields['quantity'].widget.attrs.update({'placeholder': 'Example: 20 sacks, 800 kg'})
        self.fields['notes'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Any special instructions or information (optional)'})
        self.fields['rental_type'].widget.attrs.update({'class': 'dryer-rental-type-radio'})

        selected_machine = self._selected_machine or (self.instance.machine if self.instance.pk and self.instance.machine_id else None)
        if selected_machine and selected_machine.machine_type == 'flatbed_dryer':
            self.fields['quantity'].help_text = (
                'Enter the quantity in sacks for this dryer request. Admin will review the quantity together with the service schedule.'
            )

        selected_rental_type = (
            self.data.get('rental_type')
            or self.initial.get('rental_type')
            or getattr(self.instance, 'rental_type', None)
            or 'until_dried'
        )
        if selected_rental_type == 'hourly':
            self.fields['start_time'].required = True
            self.fields['requested_hours'].required = True
            self.fields['start_time'].widget.attrs['required'] = 'required'
            self.fields['requested_hours'].widget.attrs['required'] = 'required'
        else:
            self.fields['start_time'].required = False
            self.fields['requested_hours'].required = False
            self.fields['goods_description'].required = True
            self.fields['quantity'].required = True

    def clean(self):
        cleaned_data = super().clean()
        rental_type = cleaned_data.get('rental_type') or self.data.get('rental_type') or 'until_dried'
        rental_date = cleaned_data.get('rental_date')
        start_time = cleaned_data.get('start_time')
        requested_hours = cleaned_data.get('requested_hours')
        goods_description = (cleaned_data.get('goods_description') or '').strip()
        quantity = (cleaned_data.get('quantity') or '').strip()
        machine = cleaned_data.get('machine')

        if not machine:
            posted_machine = self.data.get('machine') or self.initial.get('machine')
            if posted_machine:
                machine = Machine.objects.filter(pk=posted_machine, machine_type__in=Machine.DRYER_MACHINE_TYPES).first()

        if not machine and getattr(self, '_selected_machine', None):
            machine = self._selected_machine

        if not machine:
            machine = Machine.objects.filter(machine_type__in=Machine.DRYER_MACHINE_TYPES).order_by('name', 'pk').first()

        if not machine:
            raise ValidationError('No flatbed dryer is configured yet. Please contact the administrator.')

        if machine.status != 'available' and (not self.instance.pk or machine.pk != self.instance.machine_id):
            raise ValidationError({'machine': 'Please choose a dryer that is currently available.'})

        cleaned_data['machine'] = machine
        cleaned_data['rental_type'] = rental_type

        if rental_date and machine:
            today = timezone.now().date()
            if rental_date < today:
                raise ValidationError('Rental date cannot be in the past.')
            if rental_type == 'hourly':
                if machine.dryer_pricing_type != 'hourly':
                    raise ValidationError({
                        'rental_type': (
                            f'{machine.name} is configured as {machine.get_dryer_pricing_type_display()}. '
                            'Use the Until Dried request flow so the saved dryer pricing matches the request.'
                        )
                    })
                if not start_time:
                    raise ValidationError({'start_time': 'Start time is required for by-hour rentals.'})
                if requested_hours in [None, '']:
                    raise ValidationError({'requested_hours': 'Enter the number of hours required.'})

                opening_time = datetime.strptime('08:00', '%H:%M').time()
                closing_time = datetime.strptime('18:00', '%H:%M').time()
                if start_time < opening_time:
                    raise ValidationError('Allowed dryer rental time is only from 8:00 AM to 6:00 PM.')

                requested_hours_decimal = Decimal(str(requested_hours))
                duration_minutes = int(requested_hours_decimal * Decimal('60'))
                if duration_minutes <= 0:
                    raise ValidationError({'requested_hours': 'Requested hours must be greater than zero.'})

                start_dt = datetime.combine(rental_date, start_time)
                end_dt = start_dt + timedelta(minutes=duration_minutes)
                end_time = end_dt.time()

                if end_time > closing_time:
                    raise ValidationError({'requested_hours': 'The selected start time and hours go beyond the 6:00 PM dryer window.'})

                cleaned_data['end_time'] = end_time
                cleaned_data['requested_hours'] = requested_hours_decimal.quantize(Decimal('0.01'))

            else:
                until_dried_errors = {}
                if not goods_description:
                    until_dried_errors['goods_description'] = 'Describe the rice grain batch for an until-dried rental.'
                if not quantity:
                    until_dried_errors['quantity'] = 'Enter the rice grain quantity for an until-dried rental.'
                if until_dried_errors:
                    raise ValidationError(until_dried_errors)
                cleaned_data['start_time'] = None
                cleaned_data['end_time'] = None
                cleaned_data['requested_hours'] = None
                requested_sacks = DryerRental.parse_quantity_to_sacks(quantity)
                if requested_sacks is None or requested_sacks <= 0:
                    raise ValidationError({
                        'quantity': 'Enter the dryer quantity in sacks, for example "200 sacks".'
                    })
                available_capacity = DryerRental.available_dryer_capacity_for_date(
                    machine,
                    rental_date,
                    exclude_pk=self.instance.pk if self.instance.pk else None,
                )
                if requested_sacks > available_capacity:
                    next_available_date = DryerRental.first_dryer_date_with_capacity(
                        machine,
                        requested_sacks,
                        rental_date,
                        exclude_pk=self.instance.pk if self.instance.pk else None,
                    )
                    remaining_label = f"{available_capacity:,.2f}"
                    message = (
                        f'This dryer only has {remaining_label} sack(s) remaining on {rental_date:%B %d, %Y}. '
                        'Reduce the quantity or choose another date.'
                    )
                    if next_available_date and next_available_date != rental_date:
                        message += f' Next available date for this load: {next_available_date:%B %d, %Y}.'
                    raise ValidationError({'quantity': message})

        if self.is_admin_booking:
            renter_name = (cleaned_data.get('renter_name') or '').strip()
            selected_member = _resolve_member_user(cleaned_data.get('selected_member_id'))
            if selected_member:
                cleaned_data['renter_name'] = _display_name_for_user(selected_member)
                cleaned_data['renter_contact_number'] = selected_member.phone_number or ''
                cleaned_data['farm_location'] = _membership_farm_location(selected_member) or selected_member.address or ''
                self._resolved_booking_user = selected_member
            else:
                if not renter_name:
                    raise ValidationError({'renter_name': 'Enter a renter name or choose a suggested member.'})
                self._resolved_booking_user = _get_or_create_system_booking_user()
        else:
            self._resolved_booking_user = self.user

        return cleaned_data

    def apply_booking_identity(self, dryer_rental):
        booking_user = self._resolved_booking_user or self.user or getattr(dryer_rental, 'user', None)
        if booking_user is not None:
            dryer_rental.user = booking_user
        dryer_rental.customer_name = (self.cleaned_data.get('renter_name') or '').strip()
        dryer_rental.customer_contact_number = (self.cleaned_data.get('renter_contact_number') or '').strip()
        dryer_rental.customer_address = (self.cleaned_data.get('farm_location') or '').strip()
        if self.is_admin_booking:
            dryer_rental.payment_method = 'face_to_face'

    def save(self, commit=True):
        dryer_rental = super().save(commit=False)
        dryer_rental.rental_type = self.cleaned_data.get('rental_type') or 'until_dried'
        dryer_rental.pricing_type_snapshot = dryer_rental.rental_type
        dryer_rental.goods_description = (self.cleaned_data.get('goods_description') or '').strip()
        dryer_rental.quantity = (self.cleaned_data.get('quantity') or '').strip()
        dryer_rental.end_time = self.cleaned_data.get('end_time')
        dryer_rental.requested_hours = self.cleaned_data.get('requested_hours')
        dryer_rental.estimated_drying_days = None
        dryer_rental.solar_drying_notes = ''
        if dryer_rental.rental_type == 'hourly':
            dryer_rental.estimated_end_date = dryer_rental.rental_date
        else:
            dryer_rental.start_time = None
            dryer_rental.end_time = None
            dryer_rental.requested_hours = None
            dryer_rental.estimated_end_date = None
        if commit:
            dryer_rental.save()
        return dryer_rental


class DryerRentalApprovalForm(forms.ModelForm):
    class Meta:
        model = DryerRental
        fields = ['estimated_end_date', 'estimated_end_time', 'admin_note']
        widgets = {
            'estimated_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'estimated_end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'admin_note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estimated_end_date'].required = False
        self.fields['estimated_end_time'].required = False
        self.fields['admin_note'].required = False
        if self.instance.rental_date:
            self.fields['estimated_end_date'].widget.attrs['min'] = self.instance.rental_date.isoformat()
        if not self.fields['estimated_end_date'].initial and not self.instance.estimated_end_date:
            today = timezone.localdate()
            default_date = max(self.instance.rental_date, today) if self.instance.rental_date else today
            self.fields['estimated_end_date'].initial = default_date
        if not self.fields['estimated_end_time'].initial and not self.instance.estimated_end_time:
            self.fields['estimated_end_time'].initial = timezone.localtime().replace(second=0, microsecond=0).time()
        if self.instance.machine_id and self.instance.machine.machine_type == 'flatbed_dryer':
            self.fields['estimated_end_date'].help_text = (
                'Set the expected finish date for this request so the dryer schedule stays clear for admin review and follow-up rentals.'
            )
        else:
            self.fields['estimated_end_date'].help_text = (
                'Required when moving an until-dried request into active service so the blocked date range is clear.'
            )
        self.fields['estimated_end_time'].help_text = (
            'Set the expected completion time so pickup and dryer release are scheduled clearly.'
        )
        self.fields['admin_note'].help_text = (
            'Optional note for the renter, such as instructions to bring the goods a day early for confirmation.'
        )

    def clean(self):
        cleaned_data = super().clean()
        estimated_end_date = cleaned_data.get('estimated_end_date')
        estimated_end_time = cleaned_data.get('estimated_end_time')
        admin_note = (cleaned_data.get('admin_note') or '').strip()
        rental = self.instance

        if estimated_end_time and not estimated_end_date:
            raise ValidationError({'estimated_end_date': 'Select an estimated completion date before setting the time.'})

        if rental.is_until_dried_pricing:
            if estimated_end_date and estimated_end_date < rental.rental_date:
                raise ValidationError({'estimated_end_date': 'Estimated completion date cannot be earlier than the rental start date.'})
            if estimated_end_date and not estimated_end_time:
                raise ValidationError({'estimated_end_time': 'Enter the estimated completion time to continue.'})
            if rental.status == 'pending' and not estimated_end_date and not admin_note:
                raise ValidationError('Enter an admin note or an estimated completion date before approving this until-dried request.')
            if rental.status == 'waiting_confirmation' and not estimated_end_date:
                raise ValidationError({'estimated_end_date': 'Enter the estimated completion date to move this service into progress.'})

        cleaned_data['admin_note'] = admin_note
        return cleaned_data

