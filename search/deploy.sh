#!/bin/sh
# Build and install the search API on the VPS (Debian). Prompts for sudo.
set -eu
HOST=${1:-vps}

cd "$(dirname "$0")"
ssh "$HOST" 'rm -rf ~/search-build && mkdir -p ~/search-build/src'
scp -q Cargo.toml Cargo.lock "$HOST":search-build/
scp -q src/main.rs "$HOST":search-build/src/
scp -q search.service ../og/Caddyfile "$HOST":/tmp/
ssh -t "$HOST" "
    set -e
    sudo apt-get install -y -qq cargo >/dev/null
    cd ~/search-build && cargo build --release --locked
    sudo install -D -m 755 target/release/search /opt/search/search
    sudo install -m 644 /tmp/search.service /etc/systemd/system/search.service
    sudo install -m 644 /tmp/Caddyfile /etc/caddy/Caddyfile
    sudo systemctl daemon-reload
    sudo systemctl enable --now search
    sudo systemctl restart search
    sudo systemctl reload caddy
    rm -rf ~/search-build
"
