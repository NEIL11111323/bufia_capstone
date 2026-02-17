from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserActivityReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"

class MachineUsageReport(models.Model):
    machine_name = models.CharField(max_length=100)
    usage_type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.machine_name} - {self.usage_type}"

class RiceMillSchedulingReport(models.Model):
    schedule_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"Schedule {self.schedule_id} - {self.user.username}" 