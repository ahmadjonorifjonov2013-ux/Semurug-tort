#!/bin/bash
# 8000-port "Maktab uchun crm" loyihasi band — shuning uchun 8001 ishlatiladi.
# nginx o'rnatilgan bo'lsa, sayt http://localhost va telefonda/notebookda
# http://<bu kompyuterning IP si> orqali ochiladi.
# IP ni ko'rish:  ip -4 addr show scope global | grep inet
#
# O'zgartirishlar:
#   PORT=8010 ./start.sh            — boshqa port
#   HOST=0.0.0.0 ./start.sh         — faqat nginx'siz, to'g'ridan-to'g'ri ochish
set -e
cd "$(dirname "$0")"
source venv/bin/activate
exec python manage.py runserver "${HOST:-127.0.0.1}:${PORT:-8001}"
