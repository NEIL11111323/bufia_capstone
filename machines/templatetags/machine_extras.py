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


@register.filter
def calculate_rental_payment(rental):
    """
    Calculate rental payment based on land area (₱4,000 per hectare)
    
    Usage:
        {{ rental|calculate_rental_payment }}
    """
    if hasattr(rental, 'payment_amount') and rental.payment_amount:
        return float(rental.payment_amount)
    elif hasattr(rental, 'calculate_payment_amount'):
        try:
            return float(rental.calculate_payment_amount())
        except Exception:
            return 0
    return 0

@register.filter
def multiply(value, arg):
    """
    Multiply two numbers
    
    Usage:
        {{ value|multiply:4000 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
