# Install

Automated weekly Wazuh security review: SSH read-only to the manager, build a
one-page executive PDF, email it, schedule every Sunday 18:00.

## 1. Requirements

| Component | Notes |
|-----------|-------|
| Python 3.8+ | stdlib only — no pip packages |
| `chromium` (or `chromium-browser` / `google-chrome`) | HTML → PDF via `--print-to-pdf`. **Snap chromium can only write under `$HOME`** — keep this repo in the home dir. |
| `ssh` client | key-based, read-only access to the Wazuh manager |
| A SOCops-style `.env` | supplies `SMTP_HOST/PORT/USER/PASS` + `NOTIFY_EMAIL` |

The **manager side** needs, for the account you SSH in as:
- `sudo` (NOPASSWD or a TTY-less path) to run `collect_remote.py` as root
- readable `wazuh-install-files.tar` (for the indexer password — read in-process, never printed)
- `/var/ossec/bin/agent_control`, `/var/ossec/logs/ossec.log`, OpenSearch on `127.0.0.1:9200`

## 2. SSH key (read-only collector)

Generate a dedicated key and authorize it on the manager:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/wazuh_report -C wazuh-weekly-report -N ''
ssh-copy-id -i ~/.ssh/wazuh_report.pub <ssh-user>@<manager-host>
```

Restrict `sudo` on the manager to just the collector if you want least-privilege
(e.g. a wrapper script in `sudoers` running `python3` on stdin).

## 3. Configure

```bash
cp .env.example .env
$EDITOR .env
```

| Var | Purpose |
|-----|---------|
| `WAZUH_HOST` | manager hostname / IP |
| `WAZUH_SSH_USER` | SSH user on the manager |
| `WAZUH_SSH_KEY` | path to the private key from step 2 |
| `SOCOPS_ENV` | path to the `.env` holding `SMTP_*` + `NOTIFY_EMAIL` |
| `REPORT_EMAIL_TO` | *(optional)* override recipient; else `NOTIFY_EMAIL` |

`.env` is gitignored. No secrets are committed.

## 4. Test

```bash
./run.sh                      # collect → PDF → email (recipient from config)
./run.sh soc@example.com      # override recipient
```

Artifacts land in the repo root: `data_<date>.json`, `report_<date>.html`,
`wazuh_week_report_<date>.pdf` (all gitignored, rotated to newest 8).

## 5. Schedule (systemd, Sunday 18:00)

Edit the templates in `systemd/` — replace `youruser` and the paths — then:

```bash
sudo cp systemd/wazuh-weekly-report.service /etc/systemd/system/
sudo cp systemd/wazuh-weekly-report.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-weekly-report.timer

# verify
systemctl list-timers wazuh-weekly-report.timer
sudo systemctl start wazuh-weekly-report.service    # run once now
journalctl -u wazuh-weekly-report.service -n 20
```

The service is `Type=oneshot`; the timer is `Persistent=true` (a missed Sunday
runs at next boot). Ensure `PATH` in the unit includes `/snap/bin` if chromium
is the snap build.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `FATAL: empty collector output` | SSH/sudo failed on the manager, or OpenSearch unreachable. Test: `ssh -i <key> <user>@<host> 'sudo /var/ossec/bin/wazuh-control info'` |
| `FATAL: PDF not produced` | chromium can't write outside `$HOME` (snap) — keep repo under home; check `PATH` has the chromium binary |
| email step fails | `SOCOPS_ENV` path wrong, or `SMTP_*` / `NOTIFY_EMAIL` missing there |
| empty findings cards | no level ≥10 alerts / no disconnected agents / no integration errors in the window — expected on a quiet week |
