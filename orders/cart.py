"""Savat bilan ishlashning barcha funksiyalari (session'da saqlanadi)."""

from decimal import Decimal

from cakes.models import Cake, Option

CART_KEY = 'cart'


def get_cart(request):
    """Sessiyadagi savat: {tort_id: 'miqdor'}"""
    if CART_KEY not in request.session:
        request.session[CART_KEY] = {}
    return request.session[CART_KEY]


def add(request, cake_id, quantity=1, options=None):
    """Savatga qo'shadi. options — tanlangan variant id'lari ro'yxati."""
    cart = get_cart(request)
    key = str(cake_id)
    cart[key] = {
        'qty': int(cart.get(key, {}).get('qty', 0)) + int(quantity),
        'options': [int(o) for o in (options or [])],
        'comment': cart.get(key, {}).get('comment', ''),
    }
    request.session.modified = True
    return cart


def update(request, cake_id, quantity, options=None, comment=None):
    """Miqdorni yangilaydi (0 yoki minus — o'chiradi)."""
    cart = get_cart(request)
    key = str(cake_id)
    if quantity < 1:
        cart.pop(key, None)
    else:
        current = cart.get(key, {})
        cart[key] = {
            'qty': int(quantity),
            'options': [int(o) for o in options] if options is not None
            else current.get('options', []),
            'comment': comment if comment is not None
            else current.get('comment', ''),
        }
    request.session.modified = True
    return cart


def remove(request, cake_id):
    get_cart(request).pop(str(cake_id), None)
    request.session.modified = True


def clear(request):
    request.session[CART_KEY] = {}
    request.session.modified = True


def _normalize(cart):
    """Eski (oddiy {id: qty}) formatni yangi formatga o'tkazadi."""
    normalized = {}
    for key, value in cart.items():
        if isinstance(value, dict):
            normalized[key] = value
        else:
            normalized[key] = {'qty': int(value), 'options': [], 'comment': ''}
    return normalized


def rows(request):
    """Savatdagi ID'lar bo'yicha ma'lumotlar bazasidan oladi.

    Nomi va narxi saqlanmaydi — har doim joriy bazadan olinadi.
    Qaytaradi: (rows, total)
    """
    cart = _normalize(get_cart(request))
    if not cart:
        return [], Decimal('0')

    cakes = {
        c.pk: c
        for c in Cake.objects.filter(pk__in=[int(k) for k in cart.keys()])
                 .prefetch_related('options')
    }
    option_ids = {int(o) for v in cart.values() for o in v.get('options', [])}
    options = {o.pk: o for o in Option.objects.filter(pk__in=option_ids)}

    result, total = [], Decimal('0')
    for cake_id, value in cart.items():
        cake = cakes.get(int(cake_id))
        if not cake or not cake.is_available:
            continue

        chosen = [options[o] for o in value.get('options', []) if o in options]
        unit_price = cake.price + sum(
            (o.price_delta for o in chosen), Decimal('0')
        )
        quantity = int(value.get('qty', 1))
        subtotal = unit_price * quantity
        total += subtotal
        result.append({
            'cake': cake,
            'quantity': quantity,
            'unit_price': unit_price,
            'options': chosen,
            'comment': value.get('comment', ''),
            'subtotal': subtotal,
        })

    return result, total


def count(request):
    """Navbardagi savatdagi dona soni."""
    return sum(v.get('qty', 0) for v in _normalize(get_cart(request)).values())