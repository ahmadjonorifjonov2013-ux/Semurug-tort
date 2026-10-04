#!/bin/bash
# nginx'ga tort saytini proxy sifatida o'rnatadi -> http://localhost
# Ishlatish:  sudo bash deploy/install-nginx.sh
set -euo pipefail

CONF_SRC="$(cd "$(dirname "$0")" && pwd)/nginx-local.conf"
SITE="/etc/nginx/sites-available/tort"
LINK="/etc/nginx/sites-enabled/tort"

cp "$CONF_SRC" "$SITE"

# nginx'ning standart "Welcome" sayfasini o'chiramiz (biz default_server bo'lamiz)
rm -f /etc/nginx/sites-enabled/default

ln -sfn "$SITE" "$LINK"

nginx -t
systemctl reload nginx

echo
echo "Tayyor. Sayt: http://localhost"
echo "Django o'zi esa 8001-portda ishlashi kerak:  ./start.sh"
