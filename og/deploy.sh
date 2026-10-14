#!/bin/sh
# Install the preview-image server on the VPS (Debian). Prompts for sudo.
set -eu
HOST=${1:-vps}
FONTS=https://raw.githubusercontent.com/google/fonts/main/ofl

cd "$(dirname "$0")"
scp -q server.py og.service Caddyfile "$HOST":/tmp/
ssh -t "$HOST" "
    set -e
    sudo apt-get install -y -qq caddy python3-pil libraqm0 >/dev/null
    sudo install -d /opt/og/fonts
    sudo install -m 644 /tmp/server.py /opt/og/server.py
    [ -f /opt/og/fonts/TiroDevanagariHindi-Regular.ttf ] || sudo curl -fsSL -o /opt/og/fonts/TiroDevanagariHindi-Regular.ttf $FONTS/tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf
    [ -f /opt/og/fonts/Kalam-Bold.ttf ] || sudo curl -fsSL -o /opt/og/fonts/Kalam-Bold.ttf $FONTS/kalam/Kalam-Bold.ttf
    sudo install -m 644 /tmp/og.service /etc/systemd/system/og.service
    sudo install -m 644 /tmp/Caddyfile /etc/caddy/Caddyfile
    sudo systemctl daemon-reload
    sudo systemctl enable --now og
    sudo rm -rf /var/cache/og/*
    sudo systemctl restart og
    sudo systemctl reload caddy
"
