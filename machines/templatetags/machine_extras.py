from django import template

register = template.Library()

@register.filter
def status_color(value):
    """
    Return the appropriate Bootstrap color class based on status value.
    
    Usage:
        {{ machine.status|status_color }}
    """
    status_map = {
        'available': 'success',
        'maintenance': 'warning',
        'rented': 'danger',
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'cancelled': 'secondary',
        'completed': 'info',
    }
    
    return status_map.get(value, 'secondary')

@register.filter
def split_text(value, delimiter):
    """
    Split a string by delimiter and return result as a list.
    
    Usage:
        {{ some_text|split_text:',' }}
        {{ some_text|split_text:'\n' }}
    """
    return value.split(delimiter) 