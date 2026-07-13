from data.models import TryVoidPanelConfig

def try_voidpanel_settings(request):
    try:
        config = TryVoidPanelConfig.get_config()
        return {'try_voidpanel_config': config}
    except Exception:
        return {}
