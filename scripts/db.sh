#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Database Helper — local Postgres via Docker (Personal AI Assistant)
# Usage: ./scripts/db.sh {start|stop|reset|psql|logs|status}
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$ROOT/infra/docker-compose.yml"

POSTGRES_USER="${POSTGRES_USER:-assistant}"
POSTGRES_DB="${POSTGRES_DB:-assistant}"
CONTAINER="assistant-postgres"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[db]${NC} $*"; }
ok()   { echo -e "${GREEN}[db]${NC} $*"; }
warn() { echo -e "${YELLOW}[db]${NC} $*"; }
err()  { echo -e "${RED}[db]${NC} $*" >&2; }

do_start() {
    log "Starting Postgres container..."
    sudo docker-compose -f "$COMPOSE_FILE" up -d postgres
    log "Waiting for Postgres to be ready..."
    local i=0
    until sudo docker exec "$CONTAINER" pg_isready -U "$POSTGRES_USER" -q 2>/dev/null; do
        sleep 1; ((i++))
        if [ $i -ge 30 ]; then err "Postgres did not start in 30s"; exit 1; fi
    done
    ok "Postgres is ready on localhost:5432"
    ok "  DB:   $POSTGRES_DB"
    ok "  User: $POSTGRES_USER"
}

do_stop() {
    log "Stopping Postgres container..."
    sudo docker-compose -f "$COMPOSE_FILE" stop postgres
    ok "Postgres stopped (data volume preserved)"
}

do_reset() {
    warn "This will DELETE all data in the local database. Ctrl+C to cancel."
    sleep 3
    sudo docker-compose -f "$COMPOSE_FILE" down -v
    ok "Database volume removed. Run './scripts/db.sh start' then 'python scripts/migrate.py' to re-initialise."
}

do_psql() {
    sudo docker exec -it "$CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>/dev/null || docker exec -it "$CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
}

do_logs() {
    sudo docker-compose -f "$COMPOSE_FILE" logs -f postgres
}

do_status() {
    if sudo docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
        ok "Running"
        sudo docker exec "$CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" && ok "Accepting connections" || warn "Not accepting connections yet"
    else
        warn "Not running"
    fi
}

case "${1:-}" in
    start)  do_start ;;
    stop)   do_stop ;;
    reset)  do_reset ;;
    psql)   do_psql ;;
    logs)   do_logs ;;
    status) do_status ;;
    *)
        echo "Usage: $0 {start|stop|reset|psql|logs|status}"
        echo ""
        echo "  start   Start the Postgres Docker container"
        echo "  stop    Stop the container (data preserved)"
        echo "  reset   Destroy the container AND data volume"
        echo "  psql    Open interactive psql shell"
        echo "  logs    Stream container logs"
        echo "  status  Check if Postgres is running and accepting connections"
        exit 1
        ;;
esac
