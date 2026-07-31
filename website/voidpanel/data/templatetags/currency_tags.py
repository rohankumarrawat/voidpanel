"""
Currency template filters for VoidOnyx multi-currency support.

Usage in templates:
    {% load currency_tags %}
    {{ price|to_currency:currency_rate }}        → converts INR price to target currency
    {{ price|format_price:currency_rate }}        → converts and rounds nicely (e.g., 2.99)
"""
import math
from django import template

register = template.Library()


@register.filter
def to_currency(price_inr, rate=1):
    """Convert INR price to target currency using the given rate.

    Usage: {{ price|to_currency:currency_rate }}
    Example: {{ 149|to_currency:0.012 }} → 1.79
    """
    try:
        price = float(price_inr)
        rate = float(rate)
        converted = price * rate
        if rate == 1:
            # INR: show as integer
            return int(converted)
        else:
            # USD: round to 2 decimals, show nice price
            return f"{converted:.2f}"
    except (ValueError, TypeError):
        return price_inr


@register.filter
def format_price(price_inr, rate=1):
    """Convert and format price nicely — round USD to .99 style pricing.

    Usage: {{ price|format_price:currency_rate }}
    """
    try:
        price = float(price_inr)
        rate = float(rate)
        converted = price * rate
        if rate == 1:
            return f"{int(converted):,}"
        else:
            # Round to nearest .99 for marketing appeal
            base = math.floor(converted)
            if base < 1:
                return f"{converted:.2f}"
            return f"{base}.99"
    except (ValueError, TypeError):
        return price_inr
