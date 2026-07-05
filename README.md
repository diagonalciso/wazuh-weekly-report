# Wazuh Weekly Report

Automated weekly **Wazuh security review**: SSH read-only to the manager, render a
one-page executive **PDF**, email it, scheduled every Sunday 18:00.

All deployment specifics (host, SSH user/key, SMTP) live in a gitignored `.env`
— see **[INSTALL.md](INSTALL.md)**.

## Pipeline (`run.sh`)

1. `ssh -i "$WAZUH_SSH_KEY" "$WAZUH_SSH_USER@$WAZUH_HOST" 'sudo python3 -' < collect_remote.py`
   → runs `collect_remote.py` on the manager, emits JSON to stdout. Pulls:
   - alert volume + level distribution + daily timeline (OpenSearch `127.0.0.1:9200`, last 7d)
   - high-severity (≥10) and level-9 rule breakdowns
   - external / auth-failure source IPs
   - **agent health** (`agent_control -l` — active vs disconnected)
   - **manager errors** (`ossec.log` ERROR/CRITICAL tail + integration-failure count)
   - **cluster health** (status / nodes / shards / unassigned)
2. `build_report.py` → styled HTML with auto-flagged **P1/P2/HIGH/LOW** findings.
3. Headless Chromium `--print-to-pdf` → PDF.
4. `send_mail.py` → emails the PDF (SMTP from the configured SOCops `.env`).
5. Rotates: keeps newest 8 of each artifact.

The indexer/admin password is read from `wazuh-install-files.tar` **on the
manager, in-process only** — never printed, never committed.

## Run

```bash
cp .env.example .env && $EDITOR .env     # first time
./run.sh                                 # recipient from config
./run.sh soc@example.com                 # override recipient
```

## Schedule

systemd timer, every **Sunday 18:00** (`Persistent=true`). Unit templates in
[`systemd/`](systemd/); install steps in [INSTALL.md](INSTALL.md).

## Files

| File | Role |
|------|------|
| `run.sh` | orchestrator: config → collect → build → PDF → email → rotate |
| `collect_remote.py` | runs on the manager (as root), emits week-review JSON |
| `build_report.py` | JSON → styled HTML with auto-flagged findings |
| `send_mail.py` | emails a PDF via SMTP creds from the SOCops `.env` |
| `systemd/` | service + timer templates |
| `.env.example` | config template (copy to `.env`) |
