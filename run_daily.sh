#!/bin/bash

BASE=/Users/k.k/Desktop/ebay
LOG=$BASE/daily.log
PYTHON=/usr/bin/python3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

DISCORD_WEBHOOK="${DISCORD_ALERT_WEBHOOK:-}"

alert() {
    local msg="$1"
    log "⚠️ ALERT: $msg"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -s -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"content\":\"⚠️ pokeca daily pipeline: $msg\"}" > /dev/null
    fi
}

run_step() {
    local step="$1"
    local cmd="$2"
    local timeout_sec="${3:-300}"
    log "[$step] 開始"
    if timeout "$timeout_sec" bash -c "$cmd" >> "$LOG" 2>&1; then
        log "[$step] 完了"
        return 0
    else
        local code=$?
        if [ $code -eq 124 ]; then
            log "[$step] ★タイムアウト★ (${timeout_sec}秒超過・続行)"
            alert "$step タイムアウト (${timeout_sec}秒超過)"
        else
            log "[$step] ★失敗★ (続行)"
            alert "$step 失敗 (exit code $code)"
        fi
        return 1
    fi
}

cd "$BASE"
log "========== daily pipeline start =========="

run_step "1/6 pokeca_scan"        "$PYTHON pokeca_scan.py"        600
run_step "2/6 snkrdunk_inventory" "$PYTHON snkrdunk_inventory.py" 300
run_step "3/6 sync_from_sheets"   "$PYTHON sync_from_sheets.py"  120
run_step "4/6 report_html"        "$PYTHON report_html.py"        120
run_step "5/6 build_site"         "$PYTHON build_site.py"         120
run_step "6/6 push_to_github"     "bash $BASE/push_to_github.sh"  120

log "========== daily pipeline complete =========="
