from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0
