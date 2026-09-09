#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Convenience wrapper — runs both services
# Usage: ./scripts/run_dev.sh {start|dev|stop|restart|status|logs|kill}
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ACTION="${1:-start}"

run() {
    local svc=$1; shift
    bash "$SCRIPT_DIR/$svc.sh" "$@"
}

case "$ACTION" in
    start|stop|restart|status|kill)
        run backend "$ACTION"
        echo ""
        run frontend "$ACTION"
        ;;
    dev)
        run backend start &
        BACKEND_PID=$!
        sleep 3
        run frontend dev
        wait $BACKEND_PID 2>/dev/null || true
        ;;
    logs)
        echo "=== Backend Logs ==="
        run backend logs "${2:-30}"
        echo ""
        echo "=== Frontend Logs ==="
        run frontend logs "${2:-30}"
        ;;
    *)
        echo "Usage: $0 {start|dev|stop|restart|status|logs [N]|kill}"
        echo ""
        echo "  start    Start both (backend production + frontend production)"
        echo "  dev      Start both (backend production + frontend dev mode)"
        echo "  stop     Stop both"
        echo "  restart  Restart both"
        echo "  status   Status of both"
        echo "  logs [N] Last N lines from both"
        echo "  kill     Force-kill both ports"
        exit 1
        ;;
esac
