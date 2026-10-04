"""
Sayt sahifalari uchun oddiy rate-limit (brute-force ga qarshi).

Django'da DRF throttle faqat API uchun ishlaydi. HTML view'lar uchun
shu dekorator ishlatiladi: IP + harakat bo'yicha urinishlar hisoblanadi.

Misol:
    @rate_limit('login', limit=8, minutes=10, page='clients/login.html')
    def client_login(request): ...
"""

import hashlib
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render

DEFAULT_MESSAGE = "Juda ko'p urinish. Iltimos bir oz kutib turing."


def _client_ip(request):
    """Proksi orqasidagi haqiqiy IP ni olishga urinadi."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _key(scope, identity):
    """Uzunlik chegarasini buzmasligi uchun IP ni hash qilamiz."""
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]
    return f'rl:{scope}:{digest}'


def _bump(scope, identity, minutes):
    """Urinishlar sonini 1 ga oshiradi va yangi qiymatni qaytaradi."""
    key = _key(scope, identity)
    if cache.add(key, 1, timeout=minutes * 60):
        return 1
    try:
        return cache.incr(key)
    except ValueError:          # muddati tugagan — qayta boshlaymiz
        cache.set(key, 1, timeout=minutes * 60)
        return 1


def rate_limit(scope, limit=10, minutes=10, message=DEFAULT_MESSAGE, page=None):
    """
    Vaqt oralig'ida `limit` marta urinishga ruxsat beradi.

    limit oshilganda 429 holat qaytaradi:
      * `page` berilgan bo'lsa — o'sha shablon 'locked' kontekstida;
      * aks holda — oddiy matn.
    Faqat POST so'rovlar hisobga olinadi.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            if _bump(scope, _client_ip(request), minutes) > limit:
                if page:
                    return render(request, page, {
                        'locked': True,
                        'message': message,
                    }, status=429)
                return HttpResponse(message, status=429,
                                    content_type='text/plain')

            return view_func(request, *args, **kwargs)

        wrapper.rate_limit_scope = scope
        return wrapper

    return decorator


def reset_rate_limit(request, scope):
    """Muvaffaqiyatli urinishdan keyin hisobni tozalaydi."""
    cache.delete(_key(scope, _client_ip(request)))


__all__ = ['rate_limit', 'reset_rate_limit', 'DEFAULT_MESSAGE']
