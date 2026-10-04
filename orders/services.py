"""Telegram orqali markazga xabar yuborish (ixtiyoriy, lekin foydali).

Muhim qoidalar:
  * Hech qachon token/kalitni log'ga yozmaymiz.
  * Telegram javoblashdan oldin matnni `_escape` orqali tozalaymiz.
  * Sozlamalar `.env` dan o'qiladi (config/settings.py).
  * Testlar paytida real so'rov yuborilmaydi.
"""

import html
import json
import logging
import sys
import threading
import time
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

STATUS_EMOJI = {
    'new': '🆕',
    'confirmed': '✅',
    'in_progress': '👩‍🍳',
    'ready': '🎂',
    'delivered': '🚚',
    'cancelled': '❌',
}

_SEPARATOR = '━━━━━━━━━━━━━━━━━━━━'

# Testlar paytida haqiqiy so'rov yuborilmasligi uchun
_RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.modules


def _escape(value):
    return html.escape(str(value if value is not None else ''))


def _chat_ids():
    """TELEGRAM_CHAT_ID bir nechta bo'lishi mumkin: "123,456,-100777"."""
    raw = getattr(settings, 'TELEGRAM_CHAT_ID', '') or ''
    return [part.strip() for part in raw.split(',') if part.strip()]


def _token():
    return (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()


def _configured():
    """Token va chat id bormi?"""
    return bool(_token()) and bool(_chat_ids())


def _admin_link(pk):
    """Admin sahifasiga haqiqiy (localhost emas) havolani qaytaradi."""
    site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    if not site_url:
        return None
    if '127.0.0.1' in site_url or 'localhost' in site_url:
        return None
    return f"{site_url}/admin/orders/order/{pk}/change/"


def _keyboard(pk):
    """Xabarning pastiga tugma qo'yish uchun inline klaviatura."""
    link = _admin_link(pk)
    if not link:
        return None
    return {'inline_keyboard': [[
        {'text': '🛒 Buyurtmani ochish', 'url': link},
    ]]}


def _call(method, payload, timeout, attempts=3):
    """Telegram API ga so'rov yuboradi. Muvaffaqiyat True/False."""
    body = dict(payload)
    body['parse_mode'] = 'HTML'
    body['disable_web_page_preview'] = True

    data = json.dumps(body).encode('utf-8')
    request = urllib.request.Request(
        TELEGRAM_API.format(token=_token(), method=method),
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status == 200
        except urllib.error.HTTPError as exc:
            # 429 — limitga tegdik, kutib qayta urinamiz
            if exc.code == 429 and attempt < attempts:
                time.sleep(2 * attempt)
                continue
            logger.warning("Telegram API xatosi (%s): %s", exc.code, exc.reason)
            return False
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if attempt < attempts:
                time.sleep(1.5 * attempt)
                continue
            logger.warning("Telegram'ga ulanib bo'lmadi: %s", exc)
            return False
    return False


def _send(text, keyboard=None, timeout=None):
    """Barcha chat id ga yuboradi. Kamida bittasi muvaffaq bo'lsa True."""
    if _RUNNING_TESTS or not _configured():
        return False

    timeout = timeout or getattr(settings, 'TELEGRAM_TIMEOUT', 8)
    sent = False
    for chat_id in _chat_ids():
        payload = {'chat_id': chat_id, 'text': text}
        if keyboard:
            payload['reply_markup'] = keyboard
        # Har bir chat_id uchun alohida natija — bittasi xato bo'lsa
        # qolganlari baribir yuboriladi.
        sent = _call('sendMessage', payload, timeout) or sent
    return sent


def _dispatch(text, keyboard=None, blocking=False):
    """
    Xabarni yuboradi. `blocking=False` bo'lsa — fon rejimida (thread),
    shunda sayt sekinlashmaydi.
    """
    if _RUNNING_TESTS or not _configured():
        return False

    if blocking:
        return _send(text, keyboard)

    thread = threading.Thread(
        target=_send, args=(text, keyboard), daemon=True,
    )
    thread.start()
    return True


def _order_items_text(order):
    lines = []
    items = order.items.select_related('cake').prefetch_related('options')
    for index, item in enumerate(items, start=1):
        line = (
            f"{index}. <b>{_escape(item.cake.name)}</b> × {item.quantity} "
            f"— {item.subtotal:,.0f} so'm"
        )
        if item.options_names:
            line += f"\n     <i>{_escape(item.options_names)}</i>"
        if item.comment:
            line += f"\n     ✏️ {_escape(item.comment)}"
        lines.append(line)
    return "\n".join(lines)


def send_order_to_telegram(order, blocking=False):
    """Yangi buyurtma bo'lganda markazga xabar yuboradi.

    Xato bo'lsa sayt ishlamay qolmasin — shuning uchun barchasi
    try/except ichida. `blocking=True` — natija darhol qaytariladi.
    """
    items = _order_items_text(order)
    delivery_time = f" {order.delivery_time:%H:%M}" if order.delivery_time else ""
    text = (
        f"🎂 <b>YANGI BUYURTMA #{order.pk}</b>\n"
        f"{_SEPARATOR}\n"
        f"👤 {_escape(order.client.full_name)}\n"
        f"📞 <a href=\"tel:{_escape(order.client.phone)}\">"
        f"{_escape(order.client.phone)}</a>\n"
        f"🚚 {order.delivery_date:%d.%m.%Y}{delivery_time}\n"
        f"📍 {_escape(order.delivery_address)}\n"
        f"💳 {_escape(order.get_payment_method_display())}\n\n"
        f"{items}\n"
        f"{_SEPARATOR}\n"
        f"💰 <b>JAMI: {order.total_price:,.0f} so'm</b>"
    )
    if order.comment:
        text += f"\n\n💬 {_escape(order.comment)}"

    return _dispatch(text, keyboard=_keyboard(order.pk), blocking=blocking)


def send_status_to_telegram(order, old_status=None, blocking=False):
    """Buyurtma holati o'zgarganda markazga xabar yuboradi."""
    emoji = STATUS_EMOJI.get(order.status, 'ℹ️')
    text = (
        f"{emoji} <b>Buyurtma #{order.pk}</b> holati o'zgardi\n"
        f"Yangi holat: <b>{_escape(order.get_status_display())}</b>\n"
        f"Mijoz: {_escape(order.client.full_name)} ({_escape(order.client.phone)})\n"
        f"Yetkazish: {order.delivery_date:%d.%m.%Y}\n"
        f"Jami: {order.total_price:,.0f} so'm"
    )
    if old_status:
        old = dict(order.Status.choices).get(old_status, old_status)
        text += f"\nOldingi holat: {_escape(old)}"

    return _dispatch(text, keyboard=_keyboard(order.pk), blocking=blocking)


def send_review_to_telegram(review, blocking=False):
    """Yangi sharh qo'shilganda (admin tasdiqini kutmoqda)."""
    client = getattr(review, 'client', None)
    author = getattr(client, 'full_name', '') or review.author_name
    cake = getattr(review, 'cake', None)
    text = (
        f"⭐ <b>YANGI SHARH</b>\n"
        f"{_SEPARATOR}\n"
        f"👤 {_escape(author)}\n"
        f"🎂 {_escape(cake.name if cake else 'Umumiy')}\n"
        f"⭐️ Baho: {review.rating}/5\n\n"
        f"{_escape(review.text)}"
    )
    return _dispatch(text, blocking=blocking)


def send_contact_to_telegram(contact, blocking=False):
    """Saytdan aloqa formasi orqali xabar kelsa."""
    text = (
        f"📩 <b>YANGI XABAR</b>\n"
        f"{_SEPARATOR}\n"
        f"👤 {_escape(contact.name)}\n"
        f"📞 {_escape(contact.phone)}\n\n"
        f"{_escape(contact.message)}"
    )
    return _dispatch(text, blocking=blocking)


def broadcast(text, blocking=False):
    """Aktsiya e'loni — barcha admin chatlariga bir xil matn."""
    return _dispatch(text, blocking=blocking)


def send_test_message(blocking=True):
    """Sozlama tekshiruvi uchun. (ok, xabar) juftligini qaytaradi."""
    if _RUNNING_TESTS:
        return False, "Test muhitida yuborilmaydi"
    if not _token():
        return False, "TELEGRAM_BOT_TOKEN .env da yo'q"
    chat_ids = _chat_ids()
    if not chat_ids:
        return False, "TELEGRAM_CHAT_ID .env da yo'q"

    ok = _send(
        f"✅ Test xabari\nMarkaz: {_escape(getattr(settings, 'SITE_URL', ''))}\n"
        f"Chat ID: {', '.join(chat_ids)}",
    )
    if ok:
        return True, f"{len(chat_ids)} ta chatga yuborildi"
    return False, "Yuborilmadi — token bekor qilingan yoki chat id noto'g'ri"
