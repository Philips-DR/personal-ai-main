#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Frontend Service Manager — Next.js (Personal AI Assistant)
# Usage: ./scripts/frontend.sh {start|dev|stop|restart|status|logs [N]|kill}
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$ROOT/frontend"
PID_FILE="$FRONTEND_DIR/.pid"
LOG_FILE="$FRONTEND_DIR/server.log"
HOST="$(curl -s --connect-timeout 2 -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 30" 2>/dev/null | xargs -I{} curl -s --connect-timeout 2 -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}')"

# Read ports from .env URLs, fall back to env var overrides, then hardcoded defaults
_env_port() {
    local key="$1" default="$2"
    local url
    url=$(grep -E "^${key}=" "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'" | tr -d '[:space:]')
    if [ -n "$url" ]; then
        echo "$url" | sed 's|.*:\([0-9][0-9]*\)$|\1|' | grep -E '^[0-9]+$' || echo "$default"
    else
        echo "$default"
    fi
}
PORT="${FRONTEND_PORT:-$(_env_port FRONTEND_URL 3001)}"
BACKEND_PORT="${BACKEND_PORT:-$(_env_port BACKEND_URL 8000)}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[frontend]${NC} $*"; }
ok()   { echo -e "${GREEN}[frontend]${NC} $*"; }
warn() { echo -e "${YELLOW}[frontend]${NC} $*"; }
err()  { echo -e "${RED}[frontend]${NC} $*" >&2; }

kill_port() {
    local port=$1
    # Try fuser first (reliable on Amazon Linux), fall back to ss+kill
    if command -v fuser &>/dev/null; then
        fuser -k -KILL "${port}/tcp" 2>/dev/null || true
    else
        local pids
        pids=$(ss -tlnp "sport = :${port}" 2>/dev/null | awk 'NR>1 {match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]}' | sort -u)
        [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
    # Wait up to 3s for the port to actually free
    local i=0
    while ss -tlnp 2>/dev/null | grep -q ":${port} " && [ $i -lt 6 ]; do
        sleep 0.5; ((i++))
    done
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        err "Failed to free port $port"
        return 1
    fi
    ok "Port $port cleared"
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return
        fi
        rm -f "$PID_FILE"
    fi
    echo ""
}

is_running() { [ -n "$(get_pid)" ]; }

do_start() {
    if is_running; then
        warn "Already running (PID $(get_pid))"
        return 0
    fi

    kill_port "$PORT"

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log "Installing dependencies..."
        (cd "$FRONTEND_DIR" && npm install --silent)
    fi

    if [ ! -f "$FRONTEND_DIR/.next/BUILD_ID" ]; then
        log "No production build found — building now (this may take a minute)..."
        (cd "$FRONTEND_DIR" && BACKEND_URL="http://$HOST:$BACKEND_PORT" npx next build)
        ok "Build complete"
    fi

    log "Starting Next.js (production) on http://$HOST:$PORT"
    log "Backend API: http://$HOST:$BACKEND_PORT"
    log "Log file: $LOG_FILE"
    : > "$LOG_FILE"  # truncate stale log before fresh start

    cd "$FRONTEND_DIR"
    BACKEND_URL="http://$HOST:$BACKEND_PORT" \
    nohup npx next start \
        --hostname 0.0.0.0 \
        --port "$PORT" \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    sleep 3

    if is_running; then
        ok "Frontend started (PID $(get_pid))"
        ok "  URL: http://$HOST:$PORT"
        echo ""
        log "Tailing logs (Ctrl+C to detach — server keeps running)..."
        tail -f "$LOG_FILE"
    else
        err "Frontend failed to start. Last 20 log lines:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

do_dev() {
    if is_running; then
        warn "Already running (PID $(get_pid))"
        return 0
    fi

    kill_port "$PORT"

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log "Installing dependencies..."
        (cd "$FRONTEND_DIR" && npm install --silent)
    fi

    log "Starting Next.js (dev) on http://$HOST:$PORT"
    log "Backend API: http://$HOST:$BACKEND_PORT"
    log "Log file: $LOG_FILE"
    : > "$LOG_FILE"

    cd "$FRONTEND_DIR"
    BACKEND_URL="http://$HOST:$BACKEND_PORT" \
    nohup npx next dev \
        --hostname 0.0.0.0 \
        --port "$PORT" \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    sleep 4

    if is_running; then
        ok "Frontend started in dev mode (PID $(get_pid))"
        ok "  URL: http://$HOST:$PORT"
        echo ""
        log "Tailing logs (Ctrl+C to detach — server keeps running)..."
        tail -f "$LOG_FILE"
    else
        err "Frontend failed to start. Last 20 log lines:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

do_stop() {
    if ! is_running; then
        kill_port "$PORT" 2>/dev/null || true
        warn "Not running"
        return 0
    fi

    local pid
    pid=$(get_pid)
    log "Stopping frontend (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 2

    if kill -0 "$pid" 2>/dev/null; then
        warn "Graceful shutdown failed, force killing..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    kill_port "$PORT" 2>/dev/null || true
    rm -f "$PID_FILE"
    ok "Frontend stopped"
}

do_restart() {
    local mode="${1:-prod}"
    log "Restarting frontend ($mode)..."
    do_stop
    sleep 1
    if [ "$mode" = "dev" ]; then
        do_dev
    else
        do_start
    fi
}

do_status() {
    if is_running; then
        ok "Running (PID $(get_pid)) on port $PORT"
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT" 2>/dev/null || echo "000")
        if [ "$code" = "200" ]; then
            ok "HTTP: $code OK"
        else
            warn "HTTP: $code (may still be starting)"
        fi
    else
        warn "Not running"
        if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
            err "Port $PORT is occupied by an orphaned process"
            err "Run './scripts/frontend.sh stop' to clean up"
        fi
    fi
}

do_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        warn "No log file yet at $LOG_FILE"
        return
    fi
    local flag="${1:-}"
    if [ "$flag" = "-f" ] || [ "$flag" = "follow" ]; then
        log "Following logs (Ctrl+C to stop)..."
        echo "---"
        tail -f "$LOG_FILE"
    else
        local lines="${flag:-50}"
        log "Last $lines lines (use 'logs -f' to stream):"
        echo "---"
        tail -"$lines" "$LOG_FILE"
    fi
}

do_attach() {
    if ! is_running; then
        warn "Not running — nothing to attach to"
        return 1
    fi
    log "Attaching to logs (Ctrl+C to detach — server keeps running)..."
    echo "---"
    tail -f "$LOG_FILE"
}

# =============================================================================
case "${1:-}" in
    start)   do_start ;;
    dev)     do_dev ;;
    stop)    do_stop ;;
    restart) do_restart "${2:-prod}" ;;
    status)  do_status ;;
    logs)    do_logs "${2:-50}" ;;
    attach)  do_attach ;;
    kill)    kill_port "$PORT"; rm -f "$PID_FILE"; ok "Port $PORT cleared" ;;
    *)
        echo "Usage: $0 {start|dev|stop|restart|status|logs [-f|N]|attach|kill}"
        echo ""
        echo "  start      Build (if needed) + start Next.js production"
        echo "  dev        Start Next.js dev mode (hot reload)"
        echo "  stop       Stop gracefully, kill port on failure"
        echo "  restart    Stop + start [dev] for dev mode"
        echo "  status     Running status + HTTP check"
        echo "  logs [N]   Last N lines (default 50)"
        echo "  logs -f    Stream logs continuously"
        echo "  attach     Stream logs of the running server (Ctrl+C safe)"
        echo "  kill       Force-kill everything on port $PORT"
        exit 1
        ;;
esac
