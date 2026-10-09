#!/bin/bash
# 8000-port "Maktab uchun crm" loyihasi band — shuning uchun 8001 ishlatiladi.
# Sayt http://localhost va telefonda/notebookda http://<bu kompyuterning IP si>
# orqali ochiladi. IP ni ko'rish:  ip -4 addr show scope global | grep inet
#
# DIQQAT: HOST=0.0.0.0 — telefon va boshqa qurilmalar (Telegram'dagi
# buyurtma havolasi ham) shu kompyuterga LAN orqali ulanishi uchun kerak.
# Faqat shu kompyuterdan kirish kifoya bo'lsa: HOST=127.0.0.1 ./start.sh
#
# O'zgartirishlar:
#   PORT=8010 ./start.sh            — boshqa port
#   HOST=0.0.0.0 ./start.sh         — to'g'ridan-to'g'ri LAN'ga ochish
set -e
cd "$(dirname "$0")"
source venv/bin/activate
exec python manage.py runserver "${HOST:-0.0.0.0}:${PORT:-8001}"
