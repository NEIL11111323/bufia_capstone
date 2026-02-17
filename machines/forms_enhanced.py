"""
Enhanced forms for rental system with payment proof upload
"""
from django import forms
from .models import Rental, Machine, Maintenance
from django.core.exceptions import ValidationError
from django.utils import timezone


class RentalWithPaymentForm(forms.ModelForm):
    """
    Enhanced rental form with payment proof upload
    """
    # Additional fields
    requester_name = forms.CharField(
        max_length=200,
        required=False,
        label='Requester Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'})
    )
    
    payment_proof = forms.FileField(
        required=False,
        label='Payment Proof (Receipt/Screenshot)',
        help_text='Upload proof of payment (JPG, PNG, PDF - Max 5MB)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf'
        })
    )
    
    class Meta:
        model = Rental
        fields = ['machine', 'start_date', 'end_date', 'purpose', 'payment_method']
        widgets = {
            'machine': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        machine_id = kwargs.pop('machine_id', None)
        super().__init__(*args, **kwargs)
        
        # Limit machine choices to available machines
        if not self.instance.pk:
            self.fields['machine'].queryset = Machine.objects.filter(
                status__in=['available', 'rented']
            )
        
        # Pre-select machine if provided
        if machine_id:
            try:
                machine = Machine.objects.get(pk=machine_id)
                self.fields['machine'].initial = machine
                self.initial['machine'] = machine.pk
            except Machine.DoesNotExist:
                pass
        
        # Set minimum date to tomorrow
        self.fields['start_date'].widget.attrs['min'] = (
            timezone.now().date() + timezone.timedelta(days=1)
        ).isoformat()
    
    def clean_payment_proof(self):
        """Validate payment proof file"""
        payment_proof = self.cleaned_data.get('payment_proof')
        
        if payment_proof:
            # Check file size (max 5MB)
            if payment_proof.size > 5 * 1024 * 1024:
                raise ValidationError('File size must be less than 5MB')
            
            # Check file type
            import os
            ext = os.path.splitext(payment_proof.name)[1].lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Invalid file type. Allowed: {", ".join(valid_extensions)}'
                )
        
        return payment_proof
    
    def clean(self):
        """Enhanced validation"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        machine = cleaned_data.get('machine')
        payment_method = cleaned_data.get('payment_method')
        payment_proof = cleaned_data.get('payment_proof')
        
        # Handle disabled machine field
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
            
            # Validation 5: Check for conflicts with APPROVED rentals only
            # Pending rentals don't block the machine
            exclude_id = self.instance.pk if self.instance.pk else None
            is_available, conflicts = Rental.check_availability_for_approval(
                machine=machine,
                start_date=start_date,
                end_date=end_date,
                exclude_rental_id=exclude_id
            )
            
            if not is_available:
                conflict = conflicts.first()
                error_msg = (
                    f'This machine is already confirmed for rental from {conflict.start_date} '
                    f'to {conflict.end_date}. Please choose different dates.'
                )
                raise ValidationError(error_msg)
            
            # Validation 6: Check maintenance schedule
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
        
        # Validation 7: Payment proof required for face-to-face payment
        if payment_method == 'face_to_face' and not payment_proof and not self.instance.pk:
            raise ValidationError({
                'payment_proof': 'Payment proof is required for face-to-face payment method.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save rental with payment proof"""
        rental = super().save(commit=False)
        
        # Handle payment proof upload
        payment_proof = self.cleaned_data.get('payment_proof')
        if payment_proof:
            rental.payment_slip = payment_proof
            rental.payment_date = timezone.now()
            # Don't verify payment yet - admin will do that
            rental.payment_verified = False
        
        # Build detailed purpose from additional fields
        requester_name = self.cleaned_data.get('requester_name')
        if requester_name:
            if rental.purpose:
                rental.purpose = f"Requester: {requester_name}\n\n{rental.purpose}"
            else:
                rental.purpose = f"Requester: {requester_name}"
        
        if commit:
            rental.save()
        
        return rental


class AdminRentalApprovalForm(forms.ModelForm):
    """
    Form for admin to approve/reject rentals with payment verification
    """
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Add notes about this approval/rejection...'
        }),
        label='Admin Notes'
    )
    
    verify_payment = forms.BooleanField(
        required=False,
        initial=False,
        label='Verify Payment',
        help_text='Check this to mark payment as verified'
    )
    
    class Meta:
        model = Rental
        fields = ['status', 'payment_verified']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit status choices for approval
        self.fields['status'].choices = [
            ('pending', 'Keep Pending'),
            ('approved', 'Approve Rental'),
            ('rejected', 'Reject Rental'),
        ]
        
        # Set initial value for verify_payment
        if self.instance and self.instance.payment_verified:
            self.fields['verify_payment'].initial = True
    
    def clean(self):
        """Validate approval"""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        verify_payment = cleaned_data.get('verify_payment')
        
        # If approving, payment must be verified
        if status == 'approved' and not verify_payment:
            raise ValidationError(
                'Cannot approve rental without verifying payment. '
                'Please check "Verify Payment" checkbox.'
            )
        
        # Check for conflicts with approved rentals
        if status == 'approved':
            is_available, conflicts = Rental.check_availability_for_approval(
                machine=self.instance.machine,
                start_date=self.instance.start_date,
                end_date=self.instance.end_date,
                exclude_rental_id=self.instance.id
            )
            
            if not is_available:
                conflict = conflicts.first()
                raise ValidationError(
                    f'Cannot approve: Machine is already confirmed for rental from '
                    f'{conflict.start_date} to {conflict.end_date} '
                    f'(Rental ID: {conflict.id}, User: {conflict.user.get_full_name()})'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save with admin verification"""
        rental = super().save(commit=False)
        
        # Update payment verification
        verify_payment = self.cleaned_data.get('verify_payment')
        if verify_payment and not rental.payment_verified:
            rental.payment_verified = True
            rental.verification_date = timezone.now()
        
        # Add admin notes to purpose
        admin_notes = self.cleaned_data.get('admin_notes')
        if admin_notes:
            rental.purpose = f"{rental.purpose}\n\n--- Admin Notes ---\n{admin_notes}"
        
        if commit:
            rental.save()
        
        return rental
