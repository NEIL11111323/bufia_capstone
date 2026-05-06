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

@register.filter
def replace(value, args):
    """
    Replaces occurrences of a string with another string.
    Usage: {{ value|replace:"old,new" }} or {{ value|replace:"_":" " }}
    """
    if not args or ',' not in args:
        # If no comma, treat first arg as old and second as new (for simple cases)
        # This handles the case: replace:"_":" "
        # We need to parse it differently
        return value
    
    old, new = args.split(',', 1)
    return value.replace(old, new)

@register.filter(name='replace_underscore')
def replace_underscore(value, new_char=' '):
    """
    Replaces underscores with the specified character (default: space).
    Usage: {{ value|replace_underscore }} or {{ value|replace_underscore:" " }}
    """
    return value.replace('_', new_char)

@register.filter
def filter_by_id(queryset, id_value):
    """
    Filters a queryset by ID and returns the object's name or string representation.
    Usage: {{ machines|filter_by_id:machine_filter }}
    """
    if not id_value:
        return ''
    
    try:
        # Convert id_value to int if it's a string
        id_int = int(id_value) if isinstance(id_value, str) else id_value
        obj = queryset.get(id=id_int)
        # Try to get the name attribute, otherwise use string representation
        return getattr(obj, 'name', str(obj))
    except (ValueError, TypeError, queryset.model.DoesNotExist):
        return '' 