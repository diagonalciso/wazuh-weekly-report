# Wazuh Weekly Report

Automated weekly Wazuh security review for the manager at **192.0.2.20**.
Collects read-only from the server, renders a one-page executive **PDF**, emails it.

## Pipeline (`run.sh`)

1. `ssh -i ~/.ssh/wazuh174 ciso@192.0.2.20 'sudo python3 -' < collect_remote.py`
   → runs `collect_remote.py` on the server, emits JSON to stdout. Pulls:
   - alert volume + level distribution + daily timeline (OpenSearch `:9200`, last 7d)
   - high-severity (≥10) and level-9 rule breakdowns
   - external / auth-failure source IPs
   - **agent health** (`agent_control -l` — active vs disconnected)
   - **manager errors** (`ossec.log` ERROR/CRITICAL tail + integration-failure count)
   - **cluster health** (status / nodes / shards / unassigned)
2. `build_report.py` → styled HTML with auto-flagged P1/P2/HIGH/LOW findings.
3. Headless Chromium `--print-to-pdf` → PDF.
4. `send_mail.py` → emails the PDF (SMTP from `~/socops/.env`).
5. Rotates: keeps newest 8 of each artifact.

## Run

```bash
./run.sh                      # recipient = NOTIFY_EMAIL from ~/socops/.env
./run.sh someone@example.com  # override recipient
```

Never prints the indexer/admin password — `collect_remote.py` reads it from
`wazuh-install-files.tar` on the server and uses it only in-process.

## Config

- SSH key: `~/.ssh/wazuh174` (read-only collection)
- SMTP + default recipient: `SMTP_*` / `NOTIFY_EMAIL` in `~/socops/.env`
- PDF via `chromium` headless (snap can only write under `$HOME`)

## Schedule

systemd timer — every **Sunday 18:00**:

- `/etc/systemd/system/wazuh-weekly-report.service`  → `ExecStart=bash run.sh`
- `/etc/systemd/system/wazuh-weekly-report.timer`    → `OnCalendar=Sun 18:00`, `Persistent=true`

```bash
systemctl list-timers wazuh-weekly-report.timer
sudo systemctl start wazuh-weekly-report.service   # run now
journalctl -u wazuh-weekly-report.service -n 20
```
