#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nginx Setup & Manager — Personal AI Assistant
# Usage: ./scripts/nginx.sh {install|deploy|status|reload|stop|start|logs [N]}
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
CONF_SRC="$ROOT/infra/nginx/personal-assistant.conf"
CONF_DEST="/etc/nginx/conf.d/personal-assistant.conf"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[nginx]${NC} $*"; }
ok()   { echo -e "${GREEN}[nginx]${NC} $*"; }
warn() { echo -e "${YELLOW}[nginx]${NC} $*"; }
err()  { echo -e "${RED}[nginx]${NC} $*" >&2; }

require_root() {
    if [ "$EUID" -ne 0 ]; then
        err "This command requires sudo. Re-run as: sudo $0 $*"
        exit 1
    fi
}

do_install() {
    require_root
    log "Installing Nginx..."
    if command -v nginx &>/dev/null; then
        ok "Nginx already installed ($(nginx -v 2>&1))"
    else
        dnf install -y nginx
        ok "Nginx installed"
    fi

    # Disable the default server block so it doesn't conflict
    if [ -f /etc/nginx/nginx.conf ]; then
        # Comment out the default server block if present
        if grep -q "location / {" /etc/nginx/nginx.conf; then
            warn "Default server block found in nginx.conf — remove or comment it out manually if you see conflicts."
        fi
    fi

    systemctl enable nginx
    ok "Nginx enabled at boot"

    do_deploy
    do_start
}

do_deploy() {
    require_root
    if [ ! -f "$CONF_SRC" ]; then
        err "Config not found: $CONF_SRC"
        exit 1
    fi

    log "Deploying config: $CONF_SRC → $CONF_DEST"
    cp "$CONF_SRC" "$CONF_DEST"

    log "Testing config..."
    if nginx -t 2>&1; then
        ok "Config valid"
    else
        err "Config test failed — fix errors above before reloading"
        exit 1
    fi
}

do_reload() {
    require_root
    do_deploy
    log "Reloading Nginx..."
    systemctl reload nginx
    ok "Nginx reloaded"
}

do_start() {
    require_root
    log "Starting Nginx..."
    systemctl start nginx
    sleep 1
    if systemctl is-active --quiet nginx; then
        ok "Nginx running"
    else
        err "Nginx failed to start:"
        systemctl status nginx --no-pager -l
        exit 1
    fi
}

do_stop() {
    require_root
    log "Stopping Nginx..."
    systemctl stop nginx
    ok "Nginx stopped"
}

do_status() {
    systemctl status nginx --no-pager -l || true
}

do_logs() {
    local lines="${1:-50}"
    log "Last $lines lines from access + error logs:"
    echo "--- Access ---"
    tail -"$lines" /var/log/nginx/access.log 2>/dev/null || warn "No access log yet"
    echo "--- Error ---"
    tail -"$lines" /var/log/nginx/error.log 2>/dev/null || warn "No error log yet"
}

# =============================================================================
case "${1:-}" in
    install) do_install ;;
    deploy)  do_deploy ;;
    reload)  do_reload ;;
    start)   do_start ;;
    stop)    do_stop ;;
    status)  do_status ;;
    logs)    do_logs "${2:-50}" ;;
    *)
        echo "Usage: $0 {install|deploy|reload|start|stop|status|logs [N]}"
        echo ""
        echo "  install   Install Nginx, deploy config, and start (run once, needs sudo)"
        echo "  deploy    Copy config + nginx -t (needs sudo)"
        echo "  reload    Deploy config + reload Nginx gracefully (needs sudo)"
        echo "  start     Start Nginx (needs sudo)"
        echo "  stop      Stop Nginx (needs sudo)"
        echo "  status    Show systemd status"
        echo "  logs [N]  Show last N lines of access + error logs"
        exit 1
        ;;
esac
