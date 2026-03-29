from .models import SiteThemeSettings


THEME_LABELS = {
    SiteThemeSettings.THEME_OTHERS_3D: 'Others-3d',
    SiteThemeSettings.THEME_PORTFOLIO_3D: 'portfolio-3d',
    SiteThemeSettings.THEME_PORTFOLIO: 'portfolio',
}


def get_theme_settings():
    return SiteThemeSettings.get_solo()


def get_active_theme():
    settings = get_theme_settings()
    if settings.enable_template_switch:
        return settings.active_theme
    return SiteThemeSettings.THEME_OTHERS_3D


def get_active_theme_label():
    return THEME_LABELS.get(get_active_theme(), 'Others-3d')
