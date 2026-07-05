#!/bin/bash
# Weekly Wazuh report: collect from manager (read-only) -> HTML -> PDF -> email.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Config: load ./.env (see .env.example) then apply defaults.
[ -f "$DIR/.env" ] && set -a && . "$DIR/.env" && set +a
WAZUH_HOST="${WAZUH_HOST:-wazuh.manager.local}"
WAZUH_SSH_USER="${WAZUH_SSH_USER:-wazuh}"
WAZUH_SSH_KEY="${WAZUH_SSH_KEY:-$HOME/.ssh/wazuh_report}"
SOCOPS_ENV="${SOCOPS_ENV:-$HOME/socops/.env}"
RHOST="${WAZUH_SSH_USER}@${WAZUH_HOST}"

TS="$(date +%Y%m%d)"
JSON="$DIR/data_${TS}.json"
HTML="$DIR/report_${TS}.html"
PDF="$DIR/wazuh_week_report_${TS}.pdf"
# Recipient: arg 1, else REPORT_EMAIL_TO (.env), else NOTIFY_EMAIL from socops/.env
RECIP="${1:-${REPORT_EMAIL_TO:-}}"
if [ -z "$RECIP" ] && [ -f "$SOCOPS_ENV" ]; then
    RECIP="$(awk -F= '/^NOTIFY_EMAIL=/{gsub(/["'"'"' ]/,"",$2);print $2}' "$SOCOPS_ENV")"
fi
log(){ echo "[$(date +%H:%M:%S)] $*"; }

WAZUH_INSTALL_FILES="${WAZUH_INSTALL_FILES:-/root/wazuh-install-files.tar}"

log "collect from $WAZUH_HOST"
ssh -i "$WAZUH_SSH_KEY" -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 -o BatchMode=yes \
    "$RHOST" "sudo WAZUH_HOST='$WAZUH_HOST' WAZUH_INSTALL_FILES='$WAZUH_INSTALL_FILES' python3 -" \
    < "$DIR/collect_remote.py" > "$JSON"
[ -s "$JSON" ] || { log "FATAL: empty collector output"; exit 1; }

log "build HTML"
python3 "$DIR/build_report.py" "$HTML" < "$JSON" >/dev/null

log "render PDF"
ATTACH="$PDF"
if ! bash "$DIR/render_pdf.sh" "$HTML" "$PDF"; then
    log "no PDF engine — emailing HTML instead"; ATTACH="$HTML"
fi

log "email -> $RECIP"
python3 "$DIR/send_mail.py" "$ATTACH" "$RECIP"

# rotate: keep newest 8 of each artifact
ls -t "$DIR"/wazuh_week_report_*.pdf 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/data_*.json 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/report_*.html 2>/dev/null | tail -n +9 | xargs -r rm -f
log "done: $PDF"
