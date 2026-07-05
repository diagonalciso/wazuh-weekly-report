#!/bin/bash
# Weekly Wazuh report: collect from .174 (read-only) -> HTML -> PDF -> email.
set -euo pipefail
DIR="/home/soc/wazuh-weekly-report"
KEY="/home/soc/.ssh/wazuh174"
RHOST="ciso@192.0.2.20"
TS="$(date +%Y%m%d)"
JSON="$DIR/data_${TS}.json"
HTML="$DIR/report_${TS}.html"
PDF="$DIR/wazuh_week_report_${TS}.pdf"
# Recipient: arg 1, else NOTIFY_EMAIL from socops/.env
RECIP="${1:-}"
if [ -z "$RECIP" ]; then
    RECIP="$(awk -F= '/^NOTIFY_EMAIL=/{gsub(/["'"'"' ]/,"",$2);print $2}' /home/soc/socops/.env)"
fi
log(){ echo "[$(date +%H:%M:%S)] $*"; }

log "collect from .174"
ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o BatchMode=yes \
    "$RHOST" 'sudo python3 -' < "$DIR/collect_remote.py" > "$JSON"
[ -s "$JSON" ] || { log "FATAL: empty collector output"; exit 1; }

log "build HTML"
python3 "$DIR/build_report.py" "$HTML" < "$JSON" >/dev/null

log "render PDF (chromium)"
chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf="$PDF" "file://$HTML" 2>/dev/null
[ -s "$PDF" ] || { log "FATAL: PDF not produced"; exit 1; }

log "email -> $RECIP"
python3 "$DIR/send_mail.py" "$PDF" "$RECIP"

# rotate: keep newest 8 of each artifact
ls -t "$DIR"/wazuh_week_report_*.pdf 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/data_*.json 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/report_*.html 2>/dev/null | tail -n +9 | xargs -r rm -f
log "done: $PDF"
