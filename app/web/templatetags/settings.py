from django import template
from django.conf import settings as _settings

register = template.Library()

@register.simple_tag
def settings(name):
    return getattr(_settings, name)
