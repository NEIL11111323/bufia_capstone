from django import forms
from .models import Machine, Rental, Maintenance, PriceHistory, MachineImage, RiceMillAppointment
from django.utils import timezone
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
import os
from django.conf import settings
from django.contrib.auth import get_user_model

class MachineForm(forms.ModelForm):
    """Form for creating and updating machines"""
    class Meta:
        model = Machine
        fields = ['name', 'description', 'status', 'machine_type', 'current_price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'current_price': forms.TextInput(attrs={
                'placeholder': 'e.g., 4000/HECTARE or ₱1500/day or 1/9 sack',
            }),
        }
        labels = {
            'current_price': 'Rental Price',
        }
        help_texts = {
            'current_price': 'Enter price with unit (e.g., "4000/HECTARE", "₱1500/day", "1/9 sack")',
        }
    
    def clean_current_price(self):
        """Validate current_price field"""
        current_price = self.cleaned_data.get('current_price')
        if not current_price or not current_price.strip():
            raise ValidationError('Price field cannot be empty.')
        return current_price.strip()

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
    # Additional fields not in the model
    requester_name = forms.CharField(
        max_length=200,
        required=False,
        label='Requester Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'})
    )
    farm_area = forms.CharField(
        max_length=200,
        required=False,
        label='Farm Area/Location',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter farm location'})
    )
    operator_type = forms.ChoiceField(
        choices=[('own', 'My Own Operator'), ('bufia', 'BUFIA Operator')],
        required=False,
        label='Equipment Operator',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    service_type = forms.CharField(
        max_length=200,
        required=False,
        label='Service Type',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Plowing, Harvesting'})
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
        help_text='Enter the area of land in hectares',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01', 
            'placeholder': 'e.g., 2.5',
            'min': '0.01'
        })
    )
    payment_method = forms.ChoiceField(
        choices=[('online', 'Online Payment'), ('face_to_face', 'Face-to-Face')],
        required=False,
        label='Payment Method',
        widget=forms.RadioSelect()
    )
    
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date', 'purpose']
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Any additional notes or special requirements'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Allow pre-selecting a machine from the URL
        machine_id = kwargs.pop('machine_id', None)
        super().__init__(*args, **kwargs)
        
        # Show ALL machines regardless of status
        # Availability will be checked based on actual rental dates, not status
        # Users can see all machines but calendar will show when they're unavailable
        if not self.instance.pk:
            self.fields['machine'].queryset = Machine.objects.all().order_by('name')
        
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
    
    def clean(self):
        """Enhanced validation with comprehensive checks"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        machine = cleaned_data.get('machine')
        
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
        
        if start_date and end_date and machine:
            today = timezone.now().date()
            
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
            
            # Validation 4: Minimum advance booking (1 day)
            days_in_advance = (start_date - today).days
            if days_in_advance < 1:
                raise ValidationError({
                    'start_date': 'Bookings must be made at least 1 day in advance.'
                })
            
            # Validation 5: Check machine availability using the model method
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
            
            # Validation 6: Check maintenance schedule
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
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the rental and append additional details to purpose field"""
        rental = super().save(commit=False)
        
        # Build detailed purpose from additional fields
        details = []
        
        requester_name = self.cleaned_data.get('requester_name')
        if requester_name:
            details.append(f"Requester: {requester_name}")
        
        farm_area = self.cleaned_data.get('farm_area')
        if farm_area:
            details.append(f"Farm Area: {farm_area}")
        
        operator_type = self.cleaned_data.get('operator_type')
        if operator_type:
            operator_label = 'My Own Operator' if operator_type == 'own' else 'BUFIA Operator'
            details.append(f"Operator: {operator_label}")
        
        service_type = self.cleaned_data.get('service_type')
        if service_type:
            details.append(f"Service Type: {service_type}")
        
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
        
        if commit:
            rental.save()
        
        return rental

class AdminRentalForm(forms.ModelForm):
    """Admin form for creating rentals on behalf of users"""
    renter_name = forms.CharField(
        max_length=100,
        label='Renter Name',
        required=True,
        help_text='Enter the name of the person renting this equipment',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter renter name'})
    )
    
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date', 'purpose', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial status to approved for admin-created rentals
        if not self.instance.pk:
            self.fields['status'].initial = 'approved'
        elif self.instance.pk and self.instance.user:
            self.fields['renter_name'].initial = self.instance.user.get_full_name()

class MaintenanceForm(forms.ModelForm):
    # Add a new text field for technician name
    technician_name = forms.CharField(max_length=100, required=False, help_text="Enter technician name")
    
    class Meta:
        model = Maintenance
        fields = [
            'machine', 'maintenance_type', 'description', 'issue_reported',
            'start_date', 'end_date', 'parts_replaced',
            'technician_name', 'status'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'issue_reported': forms.Textarea(attrs={'rows': 3}),
            'parts_replaced': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize technician_name field if there's an instance with technician
        instance = kwargs.get('instance')
        if instance and instance.technician:
            self.fields['technician_name'].initial = instance.technician.get_full_name()
        
        # Remove the technician field from the form as we'll use technician_name instead
        if 'technician' in self.fields:
            del self.fields['technician']
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data
        
    def save(self, commit=True):
        """Override save method to handle technician name as text instead of foreign key"""
        maintenance = super().save(commit=False)
        
        # Clear the technician foreign key - we'll store the name in the description
        maintenance.technician = None
        
        # If technician name provided, add it to the description
        technician_name = self.cleaned_data.get('technician_name')
        if technician_name:
            # Add technician name to the description
            technician_note = f"\n\nTechnician: {technician_name}"
            if maintenance.description:
                if "Technician:" not in maintenance.description:
                    maintenance.description += technician_note
            else:
                maintenance.description = technician_note
        
        if commit:
            maintenance.save()
            
        return maintenance

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
    class Meta:
        model = RiceMillAppointment
        fields = ['machine', 'appointment_date', 'time_slot', 'rice_quantity', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # Pop machine_id and user
        machine_id = kwargs.pop('machine_id', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter machine choices to only rice mills
        self.fields['machine'].queryset = Machine.objects.filter(machine_type='rice_mill')
        self.fields['machine'].label = "Select Rice Mill"
        self.fields['machine'].empty_label = "Choose a rice mill..."
        
        # If machine_id provided, preselect it
        if machine_id:
            try:
                machine = Machine.objects.get(pk=machine_id, machine_type='rice_mill')
                self.fields['machine'].initial = machine
            except Machine.DoesNotExist:
                pass
        
        # Set the minimum date to today
        self.fields['appointment_date'].widget.attrs['min'] = timezone.now().date().isoformat()
        
        # Add Bootstrap classes and ensure fields are interactive
        self.fields['machine'].widget.attrs.update({
            'class': 'form-select',
            'required': 'required'
        })
        self.fields['appointment_date'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Select appointment date',
            'required': 'required'
        })
        self.fields['time_slot'].widget.attrs.update({
            'class': 'form-select',
            'required': 'required'
        })
        self.fields['rice_quantity'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter quantity in kg',
            'type': 'number',
            'min': '1',
            'step': '0.1',
            'required': 'required'
        })
        self.fields['notes'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Any special instructions or information (optional)',
            'rows': '3'
        })
    
    def clean(self):
        """Validate appointment date, time slot, and machine availability"""
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        time_slot = cleaned_data.get('time_slot')
        machine = cleaned_data.get('machine')
        
        if not machine:
            raise ValidationError('Please select a rice mill.')
            
        if appointment_date and time_slot and machine:
            # Ensure appointment date is not in the past
            today = timezone.now().date()
            if appointment_date < today:
                raise ValidationError('Appointment date cannot be in the past.')
            
            # Check if the time slot is available
            if not self.instance.pk:  # Only for new appointments
                # Check for overlapping approved appointments
                overlapping_appointments = RiceMillAppointment.objects.filter(
                    machine=machine,
                    appointment_date=appointment_date,
                    time_slot=time_slot,
                    status__in=['pending', 'approved']
                )
                
                if overlapping_appointments.exists():
                    raise ValidationError(
                        f'This time slot is already booked. '
                        f'Please choose a different time slot or date.'
                    )
            # For existing appointments, check for overlaps excluding this appointment
            elif self.instance.pk:
                overlapping_appointments = RiceMillAppointment.objects.filter(
                    machine=machine,
                    appointment_date=appointment_date,
                    time_slot=time_slot,
                    status__in=['pending', 'approved']
                ).exclude(pk=self.instance.pk)
                
                if overlapping_appointments.exists():
                    raise ValidationError(
                        f'This time slot is already booked. '
                        f'Please choose a different time slot or date.'
                    )
            
            # Check if machine is under maintenance or rented that day
            # Check for maintenance
            maintenance_conflicts = Maintenance.objects.filter(
                machine=machine,
                start_date__date__lte=appointment_date,
                end_date__date__gte=appointment_date,
                status__in=['scheduled', 'in_progress']
            )
            
            # Check for rentals
            rental_conflicts = Rental.objects.filter(
                machine=machine,
                start_date__lte=appointment_date,
                end_date__gte=appointment_date,
                status='approved'
            )
            
            if maintenance_conflicts.exists():
                raise ValidationError(
                    f'This machine is scheduled for maintenance on the selected date. '
                    f'Please choose a different date.'
                )
            
            if rental_conflicts.exists():
                raise ValidationError(
                    f'This machine is rented on the selected date. '
                    f'Please choose a different date.'
                )
        
        return cleaned_data 