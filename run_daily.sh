#!/bin/bash
set -e

BASE=/Users/k.k/Desktop/ebay
LOG=$BASE/daily.log
PYTHON=/usr/bin/python3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

cd "$BASE"

log "=== daily pipeline start ==="

log "Step 1/6: pokeca_scan.py"
$PYTHON pokeca_scan.py >> "$LOG" 2>&1
log "Step 1 done"

log "Step 2/6: snkrdunk_inventory.py"
$PYTHON snkrdunk_inventory.py >> "$LOG" 2>&1
log "Step 2 done"

log "Step 3/6: sync_from_sheets.py"
$PYTHON sync_from_sheets.py >> "$LOG" 2>&1
log "Step 3 done"

log "Step 4/6: report_html.py"
$PYTHON report_html.py >> "$LOG" 2>&1
log "Step 4 done"

log "Step 5/6: build_site.py"
$PYTHON build_site.py >> "$LOG" 2>&1
log "Step 5 done"

log "Step 6/6: push_to_github.sh"
bash "$BASE/push_to_github.sh" >> "$LOG" 2>&1
log "Step 6 done"

log "=== daily pipeline complete ==="
