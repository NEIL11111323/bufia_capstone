from django import forms
from decimal import Decimal
from django.utils import timezone

from .models import (
    MachineUsageReport,
    RiceMillSchedulingReport,
    RiceSale,
    RiceSaleSetting,
    UserActivityReport,
)

class UserActivityReportForm(forms.ModelForm):
    class Meta:
        model = UserActivityReport
        fields = ['user', 'activity_type', 'description']

class MachineUsageReportForm(forms.ModelForm):
    class Meta:
        model = MachineUsageReport
        fields = ['machine_name', 'usage_type', 'description']

class RiceMillSchedulingReportForm(forms.ModelForm):
    class Meta:
        model = RiceMillSchedulingReport
        fields = ['schedule_id', 'user', 'start_time', 'end_time', 'status', 'description'] 


class RiceSaleSettingForm(forms.ModelForm):
    class Meta:
        model = RiceSaleSetting
        fields = ['is_available_for_sale', 'current_price_per_sack']
        widgets = {
            'is_available_for_sale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'current_price_per_sack': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        }
        labels = {
            'is_available_for_sale': 'Allow rice sales to members',
            'current_price_per_sack': 'Price per sack',
        }


class RicePurchaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pickup_date'].widget.attrs['min'] = timezone.localdate().isoformat()
        self.fields['payment_method'].label = 'Payment Method'

    class Meta:
        model = RiceSale
        fields = ['rice_type', 'sacks', 'pickup_date', 'payment_method', 'notes']
        widgets = {
            'rice_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional rice type label'}),
            'sacks': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'pickup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional pickup or request note'}),
        }

    def clean_sacks(self):
        sacks = self.cleaned_data['sacks']
        if sacks <= 0:
            raise forms.ValidationError('Sacks to buy must be greater than zero.')
        return sacks

    def clean_pickup_date(self):
        pickup_date = self.cleaned_data['pickup_date']
        if pickup_date is None:
            raise forms.ValidationError('Pickup date is required.')
        if pickup_date < timezone.localdate():
            raise forms.ValidationError('Pickup date cannot be in the past.')
        return pickup_date


class RiceOrderPaymentForm(forms.Form):
    amount_received = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    )
