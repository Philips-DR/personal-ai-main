#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Backend Service Manager — FastAPI (Personal AI Assistant)
# Usage: ./scripts/backend.sh {start|stop|restart|status|logs [N]|kill}
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT/backend"
PID_FILE="$BACKEND_DIR/.pid"
LOG_FILE="$BACKEND_DIR/server.log"
HOST="$(curl -s --connect-timeout 2 -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 30" 2>/dev/null | xargs -I{} curl -s --connect-timeout 2 -H "X-aws-ec2-metadata-token: {}" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}')"

# Read port from .env BACKEND_URL, fall back to BACKEND_PORT env var, then 8001
_env_port() {
    local key="$1" default="$2"
    local url
    local f
    url=""
    # Same files app/config.py reads, .env.local winning; repo root kept as a
    # fallback for setups that predate the move to backend/.
    for f in "$ROOT/backend/.env.local" "$ROOT/backend/.env" "$ROOT/.env.local" "$ROOT/.env"; do
        [ -f "$f" ] || continue
        url=$(grep -E "^${key}=" "$f" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'" | tr -d '[:space:]')
        if [ -n "$url" ]; then break; fi
    done
    if [ -n "$url" ]; then
        # Extract port from URL (e.g. http://host:8001 → 8001)
        echo "$url" | sed 's|.*:\([0-9][0-9]*\)$|\1|' | grep -E '^[0-9]+$' || echo "$default"
    else
        echo "$default"
    fi
}
PORT="${BACKEND_PORT:-$(_env_port BACKEND_URL 8001)}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[backend]${NC} $*"; }
ok()   { echo -e "${GREEN}[backend]${NC} $*"; }
warn() { echo -e "${YELLOW}[backend]${NC} $*"; }
err()  { echo -e "${RED}[backend]${NC} $*" >&2; }

kill_port() {
    local port=$1
    if command -v fuser &>/dev/null; then
        fuser -k -KILL "${port}/tcp" 2>/dev/null || true
    else
        local pids
        pids=$(ss -tlnp "sport = :${port}" 2>/dev/null | awk 'NR>1 {match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]}' | sort -u)
        [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
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

    log "Starting FastAPI backend on http://$HOST:$PORT"
    log "Log file: $LOG_FILE"

    cd "$BACKEND_DIR"
    eval "$(conda shell.bash hook 2>/dev/null)"
    conda activate pa

    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --reload \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    sleep 2

    if is_running; then
        ok "Backend started (PID $(get_pid))"
        ok "  API:    http://$HOST:$PORT"
        ok "  Docs:   http://$HOST:$PORT/docs"
        ok "  Health: http://$HOST:$PORT/health"
        echo ""
        log "Tailing logs (Ctrl+C to detach — server keeps running)..."
        tail -f "$LOG_FILE"
    else
        err "Backend failed to start. Last 20 log lines:"
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
    log "Stopping backend (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 2

    if kill -0 "$pid" 2>/dev/null; then
        warn "Graceful shutdown failed, force killing..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    kill_port "$PORT" 2>/dev/null || true
    rm -f "$PID_FILE"
    ok "Backend stopped"
}

do_restart() {
    log "Restarting backend..."
    do_stop
    sleep 1
    do_start
}

do_status() {
    if is_running; then
        ok "Running (PID $(get_pid)) on port $PORT"
        local health
        health=$(curl -s "http://localhost:$PORT/health" 2>/dev/null || echo "unreachable")
        ok "Health: $health"
    else
        warn "Not running"
        if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
            err "Port $PORT is occupied by an orphaned process"
            err "Run './scripts/backend.sh stop' to clean up"
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
    stop)    do_stop ;;
    restart) do_restart ;;
    status)  do_status ;;
    logs)    do_logs "${2:-50}" ;;
    attach)  do_attach ;;
    kill)    kill_port "$PORT"; rm -f "$PID_FILE"; ok "Port $PORT cleared" ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [-f|N]|attach|kill}"
        echo ""
        echo "  start      Start backend (kills port first)"
        echo "  stop       Stop gracefully, kill port on failure"
        echo "  restart    Stop + start"
        echo "  status     Running status + health check"
        echo "  logs [N]   Last N lines (default 50)"
        echo "  logs -f    Stream logs continuously"
        echo "  attach     Stream logs of the running server (Ctrl+C safe)"
        echo "  kill       Force-kill everything on port $PORT"
        exit 1
        ;;
esac
