from django import forms
from .models import UserNotification, MachineAlert, RiceMillSchedulingAlert
from django.contrib.auth import get_user_model

User = get_user_model()

class UserNotificationForm(forms.ModelForm):
    class Meta:
        model = UserNotification
        fields = ['user', 'notification_type', 'message']

class SendNotificationForm(forms.Form):
    """Form for admins to send notifications to users"""
    NOTIFICATION_TYPES = [
        ('general', 'General Announcement'),
        ('reminder', 'Reminder'),
        ('alert', 'Alert'),
        ('update', 'System Update'),
        ('maintenance', 'Maintenance Notice'),
        ('event', 'Event Notification'),
    ]
    
    RECIPIENT_CHOICES = [
        ('all', 'All Users'),
        ('members', 'Verified Members Only'),
        ('pending', 'Pending Members'),
        ('specific', 'Specific Users'),
    ]
    
    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.RadioSelect,
        label='Send To',
        initial='all'
    )
    
    specific_users = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label='Selected Users'
    )
    
    notification_type = forms.ChoiceField(
        choices=NOTIFICATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Notification Type'
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter your notification message here...'
        }),
        label='Message'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        specific_users = cleaned_data.get('specific_users')
        
        if recipient_type == 'specific' and not specific_users:
            raise forms.ValidationError('Please select at least one user when choosing "Specific Users" option.')
        
        return cleaned_data

class MachineAlertForm(forms.ModelForm):
    class Meta:
        model = MachineAlert
        fields = ['machine_name', 'alert_type', 'message']

class RiceMillSchedulingAlertForm(forms.ModelForm):
    class Meta:
        model = RiceMillSchedulingAlert
        fields = ['schedule_id', 'user', 'alert_type', 'message'] 