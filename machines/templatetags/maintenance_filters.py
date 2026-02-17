from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the provided separator and return a list of parts"""
    if value is None:
        return []
    return value.split(arg)

@register.filter
def get_technician_name(description):
    """Extract the technician name from the description if present"""
    if description and "Technician:" in description:
        parts = description.split("Technician:")
        if len(parts) > 1:
            # Get the text after "Technician:" and before the next newline (if any)
            technician_part = parts[1].strip()
            if "\n" in technician_part:
                return technician_part.split("\n")[0]
            return technician_part
    return None 