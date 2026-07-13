from django import template

register = template.Library()

@register.filter
def cut_path(value):
    # Extract everything before the last '/'
    return value.rsplit('/', 1)[0]
