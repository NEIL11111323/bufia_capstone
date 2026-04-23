"""
Forms for sector management
"""
from django import forms
from .models import Sector


class SectorForm(forms.ModelForm):
    """Form for creating and editing sectors"""
    
    class Meta:
        model = Sector
        fields = ['sector_number', 'name', 'description', 'area_coverage', 'is_active']
        widgets = {
            'sector_number': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., North District, Riverside Area'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this sector'
            }),
            'area_coverage': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Geographic boundaries and coverage area'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'sector_number': 'Sector Number',
            'name': 'Sector Name',
            'description': 'Description',
            'area_coverage': 'Area Coverage',
            'is_active': 'Active',
        }
        help_texts = {
            'sector_number': 'Choose a unique sector number (1-10)',
            'name': 'Descriptive name for this sector',
            'description': 'Optional details about this sector',
            'area_coverage': 'Optional geographic boundaries',
            'is_active': 'Uncheck to deactivate this sector',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing sector, disable sector_number field
        if self.instance and self.instance.pk:
            self.fields['sector_number'].disabled = True
            self.fields['sector_number'].help_text = 'Sector number cannot be changed after creation'
