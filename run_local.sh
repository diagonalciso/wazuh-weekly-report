#!/bin/bash
# Weekly Wazuh report — ON-MANAGER method (no SSH).
# Runs directly on the Wazuh manager. collect_remote.py needs root
# (install-files tar, agent_control, ossec.log) so invoke this as root
# or via a root systemd unit / cron. See INSTALL.md "Method B".
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Config: load ./.env (see .env.local.example) then apply defaults.
[ -f "$DIR/.env" ] && set -a && . "$DIR/.env" && set +a
WAZUH_HOST="${WAZUH_HOST:-$(hostname)}"
WAZUH_INSTALL_FILES="${WAZUH_INSTALL_FILES:-/root/wazuh-install-files.tar}"
# SMTP: point SMTP_ENV at a file holding SMTP_HOST/PORT/USER/PASS + NOTIFY_EMAIL.
export SMTP_ENV="${SMTP_ENV:-$DIR/smtp.env}"

TS="$(date +%Y%m%d)"
JSON="$DIR/data_${TS}.json"
HTML="$DIR/report_${TS}.html"
PDF="$DIR/wazuh_week_report_${TS}.pdf"
RECIP="${1:-${REPORT_EMAIL_TO:-}}"
log(){ echo "[$(date +%H:%M:%S)] $*"; }

log "collect (local, as $(id -un))"
WAZUH_HOST="$WAZUH_HOST" WAZUH_INSTALL_FILES="$WAZUH_INSTALL_FILES" \
    python3 "$DIR/collect_remote.py" > "$JSON"
[ -s "$JSON" ] || { log "FATAL: empty collector output"; exit 1; }

log "build HTML"
python3 "$DIR/build_report.py" "$HTML" < "$JSON" >/dev/null

log "render PDF"
ATTACH="$PDF"
if bash "$DIR/render_pdf.sh" "$HTML" "$PDF"; then
    :
else
    log "no PDF engine — emailing HTML instead"
    ATTACH="$HTML"
fi

log "email -> ${RECIP:-<NOTIFY_EMAIL>}"
python3 "$DIR/send_mail.py" "$ATTACH" "$RECIP"

# rotate: keep newest 8 of each artifact
ls -t "$DIR"/wazuh_week_report_*.pdf 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/data_*.json 2>/dev/null | tail -n +9 | xargs -r rm -f
ls -t "$DIR"/report_*.html 2>/dev/null | tail -n +9 | xargs -r rm -f
log "done"
