from django import template
register = template.Library()

@register.filter
def getattr(obj, key):
    return getattr(obj, key, '')
