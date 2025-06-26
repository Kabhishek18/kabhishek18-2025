import random
from django import template

register = template.Library()

ICON_CLASSES = [
    "fas fa-microchip",
    "fas fa-code",
    "fas fa-brain",
    "fas fa-calendar",
    "fas fa-robot",
    "fas fa-laptop-code",
    "fas fa-chart-line",
    "fas fa-database"
]

@register.simple_tag
def random_icon():
    return random.choice(ICON_CLASSES)
