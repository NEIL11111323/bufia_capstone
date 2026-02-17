from django import template

register = template.Library()

@register.filter
def status_color(status):
    """
    Returns the appropriate Bootstrap color class based on the machine status.
    Usage: {{ machine.status|status_color }}
    """
    status_colors = {
        'available': 'success',
        'maintenance': 'warning',
        'rented': 'danger',
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'cancelled': 'secondary',
        'completed': 'info',
    }
    
    return status_colors.get(status, 'secondary') 