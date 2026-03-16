from django import forms
from .models import WaterIrrigationRequest, IrrigationRequestHistory

class IrrigationRequestForm(forms.ModelForm):
    """Form for farmers to create water irrigation requests"""
    
    # Add custom fields for autofill
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
    
    class Meta:
        model = WaterIrrigationRequest
        fields = [
            'requested_date', 'duration_hours', 'purpose', 'crop_type', 'area_size',
            'special_requirements'
        ]
        widgets = {
            'requested_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Rice planting, germination phase'}),
            'crop_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Rice, Corn, Vegetables'}),
            'area_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'readonly': 'readonly',
                'style': 'background-color: #f0f9f4; cursor: not-allowed;'
            }),
            'special_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text and labels
        self.fields['requested_date'].help_text = "Select the date you need irrigation"
        self.fields['duration_hours'].help_text = "How many hours of irrigation do you need?"
        self.fields['area_size'].help_text = "From your membership application"
        self.fields['area_size'].label = "Area Size (hectares)"
        
        # Autofill form with membership data if available
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
                farm_location = membership.bufia_farm_location or membership.farm_location
                if farm_location:
                    self.initial['farm_location'] = farm_location
            
            # Autofill area size
            if not self.initial.get('area_size') and membership.farm_size:
                self.initial['area_size'] = membership.farm_size


class IrrigationRequestStatusForm(forms.ModelForm):
    """Form for admins to update the status of water irrigation requests"""
    
    class Meta:
        model = WaterIrrigationRequest
        fields = ['status', 'status_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'status_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes about this status change'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status_notes'].required = True
        self.fields['status_notes'].help_text = "Please provide details about this decision"


class AdminIrrigationRequestForm(forms.ModelForm):
    """Form for admins to create irrigation requests for walk-in customers"""
    
    class Meta:
        model = WaterIrrigationRequest
        fields = [
            'farmer', 'sector', 'requested_date', 'duration_hours', 
            'purpose', 'crop_type', 'area_size', 'special_requirements'
        ]
        widgets = {
            'farmer': forms.Select(attrs={'class': 'form-select'}),
            'sector': forms.Select(attrs={'class': 'form-select'}),
            'requested_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Rice planting, germination phase'}),
            'crop_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Rice, Corn, Vegetables'}),
            'area_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'special_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text and labels
        self.fields['farmer'].help_text = "Select the farmer/member for this request"
        self.fields['sector'].help_text = "Select the irrigation sector"
        self.fields['requested_date'].help_text = "Select the date for irrigation"
        self.fields['duration_hours'].help_text = "How many hours of irrigation needed?"
        self.fields['area_size'].help_text = "Size in hectares" 