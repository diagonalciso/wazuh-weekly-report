#!/usr/bin/env python3
"""Email a PDF via SMTP creds from socops/.env. Usage: send_mail.py <pdf> [recipient]"""
import os, sys, smtplib, ssl
from email.message import EmailMessage
from pathlib import Path

# SMTP config source: $SMTP_ENV, else $SOCOPS_ENV, else ~/socops/.env
ENV = Path(os.getenv("SMTP_ENV") or os.getenv("SOCOPS_ENV")
           or (Path.home() / "socops" / ".env"))
cfg = {}
for line in ENV.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")

pdf = sys.argv[1]
to = sys.argv[2] if len(sys.argv) > 2 else cfg.get("NOTIFY_EMAIL", "")
if not to:
    sys.exit("No recipient: pass as argv[2] or set NOTIFY_EMAIL in socops/.env")
host, port = cfg["SMTP_HOST"], int(cfg["SMTP_PORT"])
user, pw = cfg["SMTP_USER"], cfg["SMTP_PASS"]

msg = EmailMessage()
msg["From"] = user
msg["To"] = to
msg["Subject"] = "Wazuh Weekly Security Review"
msg.set_content(
    "Attached: automated weekly Wazuh security review for the configured manager.\n"
    "Covers alert volume, high-severity findings, agent health, sshd hardening\n"
    "drift, external brute-force noise and ingestion health for the past 7 days.\n\n"
    "-- CisoDiagonal SOC (automated)\n"
)
data = Path(pdf).read_bytes()
if pdf.lower().endswith(".pdf"):
    maintype, subtype = "application", "pdf"
else:                                    # HTML fallback (no PDF engine on host)
    maintype, subtype = "text", "html"
msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=Path(pdf).name)

ctx = ssl.create_default_context()
with smtplib.SMTP(host, port) as s:
    s.starttls(context=ctx)
    s.login(user, pw)
    s.send_message(msg)
print(f"sent {pdf} -> {to}")
