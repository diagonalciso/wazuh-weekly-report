# Wazuh Weekly Report

> Automated weekly Wazuh SOC report — PDF summary of alerts and top rules, emailed on a schedule.

Automated weekly **Wazuh security review**: collect from the manager, render a
one-page executive **PDF** (HTML fallback if no PDF engine), email it, scheduled
every Sunday 18:00.

Two deployment methods — pick one:

| | **Method A — Remote (SSH)** | **Method B — On-manager (local)** |
|--|--|--|
| Runs on | a separate ops box | the Wazuh manager itself |
| Entry point | `run.sh` | `run_local.sh` |
| Collection | `ssh … 'sudo python3 -' < collect_remote.py` | `sudo python3 collect_remote.py` (no SSH) |
| Secrets on manager | none (browser/SMTP stay off the SIEM) | needs `smtp.env` on the manager |
| Why | keep the SIEM clean; OpenSearch `:9200` is localhost-only | fully self-contained; no SSH key, no cross-host dep |

Both share the same collector, HTML builder, PDF renderer and mailer. All
deployment specifics live in a gitignored `.env` — see **[INSTALL.md](INSTALL.md)**.

## What it collects (last 7 days)

- alert volume + level distribution + daily timeline (OpenSearch `127.0.0.1:9200`)
- high-severity (≥10) and level-9 rule breakdowns
- external / auth-failure source IPs
- **agent health** (`agent_control -l` — active vs disconnected)
- **manager errors** (`ossec.log` ERROR/CRITICAL tail + integration-failure count)
- **cluster health** (status / nodes / shards / unassigned)

Then `build_report.py` renders styled HTML with auto-flagged **P1/P2/HIGH/LOW**
findings, `render_pdf.sh` turns it into a PDF (chromium → wkhtmltopdf → weasyprint
→ libreoffice, first available wins; HTML emailed if none), `send_mail.py` sends it.

The indexer/admin password is read from `wazuh-install-files.tar` **on the
manager, in-process only** — never printed, never committed.

## Run

**Method A (remote):**
```bash
cp .env.example .env && $EDITOR .env     # host, ssh user/key, SMTP source
./run.sh                                 # recipient from config
./run.sh soc@example.com                 # override recipient
```

**Method B (on the manager, as root):**
```bash
cp .env.local.example .env && $EDITOR .env   # WAZUH_INSTALL_FILES, SMTP_ENV
cp smtp.env.example smtp.env && $EDITOR smtp.env && chmod 600 smtp.env
sudo ./run_local.sh
```

## Schedule

systemd timer, every **Sunday 18:00** (`Persistent=true`). Templates in
[`systemd/`](systemd/): `*.service`/`*.timer` for Method A,
`*-local.service`/`*-local.timer` for Method B. Steps in [INSTALL.md](INSTALL.md).

## Files

| File | Role |
|------|------|
| `run.sh` | Method A orchestrator (remote/SSH) |
| `run_local.sh` | Method B orchestrator (on-manager, no SSH) |
| `collect_remote.py` | runs on the manager (as root), emits week-review JSON |
| `build_report.py` | JSON → styled HTML with auto-flagged findings |
| `render_pdf.sh` | HTML → PDF via first available engine (HTML fallback) |
| `send_mail.py` | emails the PDF/HTML via SMTP creds from an `.env` |
| `systemd/` | service + timer templates (both methods) |
| `.env.example` | Method A config template |
| `.env.local.example` | Method B config template |
| `smtp.env.example` | Method B SMTP creds template |
