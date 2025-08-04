from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary.
    Usage: {{ dict|get_item:key }}
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_nested_item(dictionary, keys):
    """
    Template filter to get a nested item from a dictionary.
    Usage: {{ dict|get_nested_item:"key1.key2" }}
    """
    if not dictionary or not isinstance(dictionary, dict):
        return None
    
    try:
        keys_list = keys.split('.')
        result = dictionary
        for key in keys_list:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result
    except (AttributeError, KeyError):
        return None

@register.filter
def has_key(dictionary, key):
    """
    Template filter to check if a dictionary has a specific key.
    Usage: {% if dict|has_key:"key" %}
    """
    if dictionary and isinstance(dictionary, dict):
        return key in dictionary
    return False