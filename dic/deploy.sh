#!/bin/sh
# Build and install the dictionary backend on the VPS (Debian). Prompts for sudo.
set -eu
HOST=${1:-vps}
FONTS=https://raw.githubusercontent.com/google/fonts/main/ofl

cd "$(dirname "$0")"
ssh "$HOST" 'rm -rf ~/dic-build && mkdir -p ~/dic-build/src'
scp -q Cargo.toml Cargo.lock "$HOST":dic-build/
scp -q src/*.rs "$HOST":dic-build/src/
scp -q dic.service Caddyfile "$HOST":/tmp/
ssh -t "$HOST" "
    set -e
    sudo apt-get install -y -qq caddy cargo >/dev/null
    cd ~/dic-build && cargo build --release --locked
    sudo install -D -m 755 target/release/dic /opt/dic/dic
    sudo install -d /opt/dic/fonts
    [ -f /opt/dic/fonts/TiroDevanagariHindi-Regular.ttf ] || sudo curl -fsSL -o /opt/dic/fonts/TiroDevanagariHindi-Regular.ttf $FONTS/tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf
    [ -f /opt/dic/fonts/Kalam-Bold.ttf ] || sudo curl -fsSL -o /opt/dic/fonts/Kalam-Bold.ttf $FONTS/kalam/Kalam-Bold.ttf
    sudo install -m 644 /tmp/dic.service /etc/systemd/system/dic.service
    sudo install -m 644 /tmp/Caddyfile /etc/caddy/Caddyfile
    # dic replaces the separate search and og services.
    for old in search og; do
        sudo systemctl disable --now \$old 2>/dev/null || true
        sudo rm -f /etc/systemd/system/\$old.service
    done
    sudo rm -rf /opt/search /opt/og
    sudo systemctl daemon-reload
    sudo systemctl enable dic
    sudo rm -rf /var/cache/dic/*
    sudo systemctl restart dic
    sudo systemctl reload caddy
    rm -rf ~/dic-build
"
