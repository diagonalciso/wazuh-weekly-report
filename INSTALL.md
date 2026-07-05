# Install

Automated weekly Wazuh security review: collect from the manager, build a
one-page executive PDF (HTML fallback), email it, schedule every Sunday 18:00.

Choose a method:

- **Method A — Remote (SSH):** runs on a separate ops box, SSHes into the
  manager read-only. Keeps the browser, SMTP creds and schedule **off** the SIEM.
- **Method B — On-manager (local):** runs directly on the Wazuh manager, no SSH.
  Self-contained; needs an `smtp.env` on the manager.

---

## Method A — Remote (SSH)

### 1. Requirements (ops box)

| Component | Notes |
|-----------|-------|
| Python 3.8+ | stdlib only — no pip packages |
| a PDF engine | `chromium` / `wkhtmltopdf` / `weasyprint` / `libreoffice`. **Snap chromium can only write under `$HOME`** — keep this repo in the home dir. Without any engine, the report is emailed as HTML. |
| `ssh` client | key-based, read-only access to the manager |
| an `.env` with SMTP | `SMTP_HOST/PORT/USER/PASS` + `NOTIFY_EMAIL` (e.g. a SOCops `.env`) |

The **manager side** needs, for the SSH account:
- `sudo` to run `collect_remote.py` as root
- readable `wazuh-install-files.tar` (indexer password — read in-process, never printed)
- `/var/ossec/bin/agent_control`, `/var/ossec/logs/ossec.log`, OpenSearch on `127.0.0.1:9200`

### 2. SSH key (read-only collector)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/wazuh_report -C wazuh-weekly-report -N ''
ssh-copy-id -i ~/.ssh/wazuh_report.pub <ssh-user>@<manager-host>
```

### 3. Configure

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
| `WAZUH_INSTALL_FILES` | path on the manager to the install-files tar |
| `REPORT_EMAIL_TO` | *(optional)* override recipient |

### 4. Test

```bash
./run.sh                      # collect → PDF → email (recipient from config)
./run.sh soc@example.com      # override recipient
```

### 5. Schedule (systemd, Sunday 18:00)

Edit `systemd/wazuh-weekly-report.service` — replace `youruser` and paths — then:

```bash
sudo cp systemd/wazuh-weekly-report.service /etc/systemd/system/
sudo cp systemd/wazuh-weekly-report.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-weekly-report.timer
systemctl list-timers wazuh-weekly-report.timer
```

---

## Method B — On-manager (local, no SSH)

Runs directly on the Wazuh manager. `collect_remote.py` needs root (install-files
tar, `agent_control`, `ossec.log`), so the runner executes as root.

### 1. Requirements (manager)

| Component | Notes |
|-----------|-------|
| Python 3.8+ | stdlib only |
| a PDF engine | optional — if none present, the report is emailed as **HTML** (no browser needed on the SIEM) |
| outbound SMTP | manager must reach your mail relay (e.g. `:587`) |

### 2. Deploy the repo on the manager

```bash
sudo git clone <this-repo> /opt/wazuh-weekly-report
cd /opt/wazuh-weekly-report
```

### 3. Configure

```bash
sudo cp .env.local.example .env && sudo $EDITOR .env
sudo cp smtp.env.example smtp.env && sudo $EDITOR smtp.env && sudo chmod 600 smtp.env
```

`.env` (Method B):

| Var | Purpose |
|-----|---------|
| `WAZUH_HOST` | label on the report (defaults to `hostname`) |
| `WAZUH_INSTALL_FILES` | path to the install-files tar (indexer password) |
| `SMTP_ENV` | path to `smtp.env` (SMTP creds) |
| `REPORT_EMAIL_TO` | *(optional)* override recipient |

`smtp.env`: `SMTP_HOST/PORT/USER/PASS` + `NOTIFY_EMAIL`. Both `smtp.env` and
`.env` are gitignored.

### 4. Test

```bash
sudo ./run_local.sh
sudo ./run_local.sh soc@example.com
```

### 5. Schedule (systemd on the manager, Sunday 18:00)

```bash
sudo cp systemd/wazuh-weekly-report-local.service /etc/systemd/system/
sudo cp systemd/wazuh-weekly-report-local.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-weekly-report-local.timer
systemctl list-timers wazuh-weekly-report-local.timer
```

---

## Notes

- Artifacts land in the repo root: `data_<date>.json`, `report_<date>.html`,
  `wazuh_week_report_<date>.pdf` (all gitignored, rotated to newest 8).
- The service is `Type=oneshot`; the timer is `Persistent=true` (a missed Sunday
  runs at next boot).

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `FATAL: empty collector output` | (A) SSH/sudo failed or OpenSearch unreachable — `ssh -i <key> <user>@<host> 'sudo /var/ossec/bin/wazuh-control info'`; (B) not run as root, or install-tar path wrong |
| emailed HTML instead of PDF | no PDF engine on the host — install `chromium`/`wkhtmltopdf`/`weasyprint`, or accept HTML |
| snap chromium writes nothing | it can only write under `$HOME` — keep the repo in the home dir; ensure `PATH` has `/snap/bin` |
| email step fails | `SMTP_ENV`/`SOCOPS_ENV` path wrong, or `SMTP_*`/`NOTIFY_EMAIL` missing; (B) manager can't reach the SMTP relay |
| empty findings cards | no level ≥10 alerts / no disconnected agents / no integration errors in the window — expected on a quiet week |
