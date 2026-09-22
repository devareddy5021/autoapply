from django import template

register = template.Library()

@register.filter(name='dict_lookup')
def dict_lookup(dictionary, key):
    """Retrieves value from dictionary by key in Django templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
