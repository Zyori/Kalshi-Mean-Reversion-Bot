#!/usr/bin/env bash
set -euo pipefail

# Run on VPS as root (or with sudo)
# Usage: bash deploy/setup.sh

APP_DIR="/opt/kalshi-mrb"
APP_USER="andrew"
REPO="https://github.com/Zyori/Kalshi-Mean-Reversion-Bot.git"

echo "=== Kalshi MRB VPS Setup ==="

# System deps
apt-get update
apt-get install -y python3.12 python3.12-venv git nginx certbot python3-certbot-nginx nodejs npm

# Install uv
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Clone or pull
if [ -d "$APP_DIR" ]; then
    echo "Updating existing repo..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "Cloning repo..."
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Backend setup
echo "=== Setting up backend ==="
cd "$APP_DIR/backend"
su - "$APP_USER" -c "cd $APP_DIR/backend && uv sync --extra dev"
su - "$APP_USER" -c "cd $APP_DIR/backend && uv run alembic upgrade head"

# Dashboard build
echo "=== Building dashboard ==="
cd "$APP_DIR/dashboard"
npm install
npm run build

# Systemd service
echo "=== Installing systemd service ==="
cp "$APP_DIR/deploy/kalshi-mrb.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable kalshi-mrb
systemctl restart kalshi-mrb

# Nginx
echo "=== Configuring nginx ==="
cp "$APP_DIR/deploy/nginx-kalshi-mrb.conf" /etc/nginx/sites-available/kalshi-mrb
ln -sf /etc/nginx/sites-available/kalshi-mrb /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "=== Done ==="
echo "Backend: systemctl status kalshi-mrb"
echo "Logs:    journalctl -u kalshi-mrb -f"
echo ""
echo "Remaining manual steps:"
echo "  1. Create /opt/kalshi-mrb/backend/.env with API keys"
echo "  2. Run: certbot --nginx -d mrb.lutz.bot"
echo "  3. Restart: systemctl restart kalshi-mrb"
