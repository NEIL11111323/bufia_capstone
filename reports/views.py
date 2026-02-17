from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserActivityReportForm, MachineUsageReportForm, RiceMillSchedulingReportForm
from .models import UserActivityReport, MachineUsageReport, RiceMillSchedulingReport

@login_required
def user_activity_report(request):
    if request.method == 'POST':
        form = UserActivityReportForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_activity_report')
    else:
        form = UserActivityReportForm()
    reports = UserActivityReport.objects.all()
    return render(request, 'reports/user_activity_report.html', {'form': form, 'reports': reports})

@login_required
def machine_usage_report(request):
    if request.method == 'POST':
        form = MachineUsageReportForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('machine_usage_report')
    else:
        form = MachineUsageReportForm()
    reports = MachineUsageReport.objects.all()
    return render(request, 'reports/machine_usage_report.html', {'form': form, 'reports': reports})

@login_required
def rice_mill_scheduling_report(request):
    if request.method == 'POST':
        form = RiceMillSchedulingReportForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('rice_mill_scheduling_report')
    else:
        form = RiceMillSchedulingReportForm()
    reports = RiceMillSchedulingReport.objects.all()
    return render(request, 'reports/rice_mill_scheduling_report.html', {'form': form, 'reports': reports}) 