from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator


class Operator(models.Model):
    """Operator model for managing machine operators"""
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('inactive', 'Inactive'),
    ]
    
    # Link to user account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='operator_profile'
    )
    
    # Operator identification
    operator_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Custom operator ID (e.g., OP-001)"
    )
    
    # Contact information
    contact_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Enter a valid phone number"
        )]
    )
    address = models.TextField()
    
    # Assignment and status
    current_machine = models.ForeignKey(
        'Machine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_operator',
        help_text="Currently assigned machine"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    
    # Employment details
    hire_date = models.DateField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['operator_id']
        indexes = [
            models.Index(fields=['operator_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.operator_id} - {self.user.get_full_name()}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def active_tasks_count(self):
        """Count of active tasks assigned to this operator"""
        return self.tasks.filter(status__in=['pending', 'in_progress']).count()
    
    @property
    def completed_tasks_count(self):
        """Count of completed tasks"""
        return self.tasks.filter(status='completed').count()
    
    def get_current_assignments(self):
        """Get current rental assignments"""
        return self.user.operator_rentals.filter(
            status__in=['approved', 'in_progress']
        ).select_related('machine', 'user')


class OperatorTask(models.Model):
    """Track operator task assignments"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('rental', 'Equipment Rental'),
        ('rice_mill', 'Rice Milling'),
        ('irrigation', 'Irrigation'),
    ]
    
    # Task identification
    operator = models.ForeignKey(
        Operator,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    machine = models.ForeignKey(
        'Machine',
        on_delete=models.CASCADE,
        related_name='operator_tasks'
    )
    
    # Service details
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_tasks',
        help_text="Farmer requesting service"
    )
    
    # Link to rental if applicable
    rental = models.ForeignKey(
        'Rental',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='operator_tasks'
    )
    
    # Task status and scheduling
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    scheduled_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    
    # Additional details
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date', '-created_at']
        indexes = [
            models.Index(fields=['operator', 'status']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def __str__(self):
        return f"{self.operator.operator_id} - {self.machine.name} - {self.scheduled_date}"
