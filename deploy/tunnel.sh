#!/bin/bash
# Bepul ochiq manzil: saytni shu kompyuterdan tashqariga ochadi
# (telefondan, do'stdan — istalgan joydan kirish mumkin).
# Cloudflare "quick tunnel" ishlatiladi: hisob va domain kerak emas.
#
#   ./deploy/tunnel.sh start    — ishga tushirish
#   ./deploy/tunnel.sh stop     — to'xtatish
#   ./deploy/tunnel.sh status   — holati
#   ./deploy/tunnel.sh url      — ochiq manzilni chiqarish
#
# DIQQAT: bu kompyuter yoniq va internet ulangan bo'lishi kerak.
# Manzil har "start" da yangilanadi (Cloudflare beradi).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RUN_DIR="$ROOT/deploy/.run"
URL_FILE="$ROOT/deploy/tunnel-url.txt"
GUNICORN_PID="$RUN_DIR/gunicorn.pid"
TUNNEL_PID="$RUN_DIR/cloudflared.pid"
TUNNEL_LOG="$RUN_DIR/cloudflared.log"
PORT="${PORT:-8001}"

CLOUDFLARED="$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")"

mkdir -p "$RUN_DIR"

alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

wait_for_django() {
    # SECURE_SSL_REDIRECT yoqligi uchun 301 qaytadi — javob borligi muhim.
    for _ in $(seq 1 40); do
        if curl -sS -o /dev/null --max-time 3 "http://127.0.0.1:$PORT/" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
    done
    return 1
}

start() {
    if alive "$GUNICORN_PID"; then
        echo "Django allaqachon ishlayapti (PID $(cat "$GUNICORN_PID"))."
    else
        # Eski jarayon qolib ketgan bo'lsa, port bo'shligini kutamiz.
        for _ in $(seq 1 20); do
            if ! curl -sS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/" 2>/dev/null; then
                break
            fi
            sleep 0.5
        done
        [ -f .env.production ] || {
            echo ".env.production yo'q. Yaratish:"
            echo "  cp deploy/env.production.example .env.production"
            echo "  va ichidagi DJANGO_SECRET_KEY ni almashtiring."
            exit 1
        }
        echo "Statik fayllar yig'ilmoqda..."
        DJANGO_ENV_FILE=.env.production venv/bin/python manage.py collectstatic --noinput >/dev/null

        echo "Django (gunicorn) $PORT-portda ishga tushirilmoqda..."
        DJANGO_ENV_FILE=.env.production venv/bin/gunicorn config.wsgi:application \
            --bind "127.0.0.1:$PORT" \
            --workers 3 \
            --timeout 60 \
            --access-logfile "$RUN_DIR/access.log" \
            --error-logfile "$RUN_DIR/error.log" \
            --pid "$GUNICORN_PID" \
            --daemon

        wait_for_django || {
            echo "Django javob bermadi. Xato: $RUN_DIR/error.log"
            exit 1
        }
        echo "Django tayyor."
    fi

    if alive "$TUNNEL_PID"; then
        echo "Tunnel allaqachon ishlamoqda."
    else
        rm -f "$URL_FILE"
        echo "Ochiq tunnel yaratilmoqda (Cloudflare)..."
        nohup "$CLOUDFLARED" tunnel --no-autoupdate \
            --url "http://127.0.0.1:$PORT" >"$TUNNEL_LOG" 2>&1 &
        echo $! >"$TUNNEL_PID"

        for _ in $(seq 1 60); do
            url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)"
            [ -n "$url" ] && break
            sleep 1
        done

        if [ -z "${url:-}" ]; then
            echo "Tunnel manzili topilmadi. Log: $TUNNEL_LOG"
            echo "Cloudflare bugun ko'p so'rov olgan bo'lishi mumkin — bir daqiqa kutib qayta urinib ko'ring."
            exit 1
        fi

        printf '%s\n' "$url" >"$URL_FILE"
        # Telegram xabarlaridagi havolalar to'g'ri bo'lishi uchun
        if [ "$(grep -c '^SITE_URL=' .env.production)" -gt 0 ]; then
            sed -i "s|^SITE_URL=.*|SITE_URL=$url|" .env.production
            DJANGO_ENV_FILE=.env.production venv/bin/python manage.py shell -c \
                "from orders import services; services.broadcast('Sayt yangi manzilga ko\'chdi: $url')" \
                >/dev/null 2>&1 || true
        fi
        echo "Tunnel tayyor."
    fi

    echo
    echo "Ochiq manzil: $(cat "$URL_FILE")"
    echo "Uni telefon brauzerida oching. Kompyuter o'chmasligi kerak."
}

stop() {
    for pid_file in "$TUNNEL_PID" "$GUNICORN_PID"; do
        if alive "$pid_file"; then
            kill "$(cat "$pid_file")" 2>/dev/null && echo "To'xtatildi: $(basename "$pid_file")"
        fi
    done

    # Jarayonlar to'liq tugashini kutamiz — aks holda port bo'sh bo'lmaydi.
    for _ in $(seq 1 30); do
        if ! alive "$GUNICORN_PID" && ! alive "$TUNNEL_PID"; then
            break
        fi
        sleep 0.5
    done
    for pid_file in "$TUNNEL_PID" "$GUNICORN_PID"; do
        alive "$pid_file" && kill -9 "$(cat "$pid_file")" 2>/dev/null || true
        rm -f "$pid_file"
    done

    rm -f "$URL_FILE"
    echo "To'xtatildi."
}

status() {
    alive "$GUNICORN_PID" && echo "Django: ishlamoqda" || echo "Django: to'xtagan"
    if alive "$TUNNEL_PID" && [ -f "$URL_FILE" ]; then
        echo "Tunnel: ishlamoqda -> $(cat "$URL_FILE")"
    else
        echo "Tunnel: to'xtagan"
    fi
}

case "${1:-start}" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    status) status ;;
    url) cat "$URL_FILE" 2>/dev/null || echo "Tunnel ishlamayapti" ;;
    *) echo "Ishlatish: $0 {start|stop|restart|status|url}"; exit 1 ;;
esac
