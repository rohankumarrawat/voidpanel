from data.models import TryVoidPanelConfig

def try_voidpanel_settings(request):
    try:
        config = TryVoidPanelConfig.get_config()
        return {'try_voidpanel_config': config}
    except Exception:
        return {}


def site_context(request):
    """Inject site_id, is_voidonyx, is_india, and currency info into every template."""
    return {
        'site_id': getattr(request, 'site_id', 'voidpanel'),
        'is_voidonyx': getattr(request, 'is_voidonyx', False),
        'is_india': getattr(request, 'is_india', True),
        'currency_symbol': getattr(request, 'currency_symbol', '₹'),
        'currency_code': getattr(request, 'currency_code', 'INR'),
        'currency_rate': getattr(request, 'currency_rate', 1),
    }

