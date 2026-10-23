#!/usr/bin/env bash
# Runs Chunky pregeneration only while no players are online and enough disk space remains.
set -u

RADIUS="${CHUNKY_RADIUS:-15000}"
MIN_FREE_GB="${CHUNKY_MIN_FREE_GB:-20}"
POLL_SECONDS="${CHUNKY_POLL_SECONDS:-10}"
DATA_DIR="${CHUNKY_DATA_DIR:-/data}"
MARKER="${DATA_DIR}/.chunky-pregen-r${RADIUS}-started"
MIN_FREE_KB=$((MIN_FREE_GB * 1024 * 1024))

# unknown | running | paused
state=unknown

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

rcon() { rcon-cli --host "${RCON_HOST:-minecraft}" --port "${RCON_PORT:-25575}" --password "${RCON_PASSWORD:?RCON_PASSWORD is required}" "$@"; }

players_online() {
  local out
  out=$(rcon list 2>/dev/null) || return 1
  echo "$out" | sed -n 's/.*There are \([0-9][0-9]*\) of a max.*/\1/p' | head -n1 | grep -E '^[0-9]+$'
}

free_kb() { df -Pk "$DATA_DIR" | awk 'NR==2 {print $4}'; }

initialize() {
  log "Starting Chunky pregeneration: overworld, spawn center, circle, radius ${RADIUS}."
  rcon chunky world minecraft:overworld &&
    rcon chunky spawn &&
    rcon chunky shape circle &&
    rcon chunky radius "$RADIUS" &&
    rcon chunky start &&
    touch "$MARKER"
}

log "Chunky scheduler started (radius=${RADIUS}, min free=${MIN_FREE_GB}GiB, poll=${POLL_SECONDS}s)."
while :; do
  if ! players=$(players_online); then
    [ "$state" != unknown ] && log "RCON unavailable; waiting for the server."
    state=unknown
    sleep "$POLL_SECONDS"
    continue
  fi

  free=$(free_kb)
  if [ "$players" -gt 0 ] || [ "${free:-0}" -lt "$MIN_FREE_KB" ]; then
    if [ "$state" != paused ]; then
      if [ "$players" -gt 0 ]; then reason="${players} player(s) online"; else reason="free space below ${MIN_FREE_GB}GiB"; fi
      log "Pausing Chunky: ${reason}."
      rcon chunky pause >/dev/null 2>&1
      state=paused
    fi
  elif [ "$state" != running ]; then
    if [ ! -f "$MARKER" ]; then
      initialize || { log "Chunky initialization failed; retrying."; sleep "$POLL_SECONDS"; continue; }
    else
      log "No players online; continuing Chunky: $(rcon chunky continue 2>&1 | tr '\n' ' ')"
    fi
    state=running
  fi
  sleep "$POLL_SECONDS"
done
