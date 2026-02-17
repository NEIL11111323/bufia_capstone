from django import forms
from .models import UserActivityReport, MachineUsageReport, RiceMillSchedulingReport

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