from .signals import get_settings


def site_settings(request):
    """Barcha shablonlarga sayt sozlamalarini beradi."""
    return {'settings_obj': get_settings()}


def cart_badge(request):
    """Navbar'dagi savat sonini beradi (savat bo'sh bo'lsa ham xatosiz)."""
    from orders.cart import count
    return {'cart_count': count(request)}