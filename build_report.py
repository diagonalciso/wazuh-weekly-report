#!/usr/bin/env python3
"""Read collector JSON on stdin, write styled HTML report to argv[1]."""
import json, sys, html

d = json.load(sys.stdin)
out = sys.argv[1]

def esc(s): return html.escape(str(s))

lvl = {k: v for k, v in d.get("by_level", [])}
n_l10 = sum(v for k, v in lvl.items() if k >= 10)
n_l9 = lvl.get(9, 0)
agents = d.get("agents", [])
down = [a for a in agents if a[2] != "Active" and "Local" not in a[2]]
up = len(agents) - len(down)
iris = d.get("iris_errors", 0)
cl = d.get("cluster", {})

# auto-flagged findings
cards = []
if iris:
    cards.append(("p1", "b1", "P1",
        "Integration errors in ossec.log",
        f"<p><b>{iris}</b> integration/script ERROR lines in the manager log this period "
        f"(e.g. <code>custom-wazuh_iris.py</code> exit 1). Noisy + likely non-functional. "
        f"<b>Action:</b> fix or disable the failing integration.</p>"))
if down:
    rows = "".join(f"<tr><td>{esc(i)}</td><td>{esc(n)}</td><td>{esc(s)}</td></tr>" for i, n, s in down)
    cards.append(("p2", "b2", "P2",
        f"{len(down)} agent(s) not Active",
        f"<table><tr><th>ID</th><th>Name</th><th>State</th></tr>{rows}</table>"
        f"<p><b>Action:</b> confirm which are real endpoints; investigate genuine offline hosts. "
        f"(Some IDs may be simulated.)</p>"))
if d.get("high_rules"):
    rows = "".join(f"<tr><td>{c}</td><td>{esc(r)}</td></tr>" for c, r in d["high_rules"])
    cards.append(("p3", "b3", "HIGH",
        f"High-severity alerts (level ≥ 10): {d.get('high_total',0)}",
        f"<table><tr><th>Hits</th><th>Rule</th></tr>{rows}</table>"))
if d.get("brute_ips"):
    rows = "".join(f"<tr><td>{esc(ip)}</td><td>{c}</td></tr>" for c, ip in d["brute_ips"])
    cards.append(("lo", "blo", "LOW",
        "External / auth-failure source IPs",
        f"<table><tr><th>Src IP</th><th>Hits</th></tr>{rows}</table>"
        f"<p>Review any sustained source; confirm SSH exposure is intended/firewalled.</p>"))

cards_html = ""
for cls, bcls, tag, title, body in cards:
    cards_html += (f'<div class="card {cls}"><h3><span class="badge {bcls}">{tag}</span>'
                   f'{esc(title)}</h3>{body}</div>')

l9_html = ""
if d.get("l9_rules"):
    rows = "".join(f"<tr><td>{c}</td><td>{esc(r)}</td></tr>" for c, r in d["l9_rules"])
    l9_html = f'<h2>Level 9 rules</h2><table><tr><th>Hits</th><th>Rule</th></tr>{rows}</table>'

lvl_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in d.get("by_level", []))
tl_rows = "".join(f"<tr><td>{esc(day)}</td><td>{c:,}</td></tr>" for day, c in d.get("timeline", []))
gaps = [day for day, c in d.get("timeline", []) if c == 0]
ing_note = ("<span class='ok'>— OK</span>" if not gaps
            else f"<span style='color:#c0392b'>— {len(gaps)} zero-count day(s): {', '.join(gaps)}</span>")

cl_line = (f"{cl.get('status','?')} · {cl.get('nodes','?')} node(s) · "
           f"{cl.get('active_shards','?')} active shards · {cl.get('unassigned','?')} unassigned"
           if cl else "unavailable")
cl_class = "ok" if cl.get("status") == "green" else "warn"

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:18mm 16mm; }}
*{{box-sizing:border-box}}
body{{font:11pt/1.45 "DejaVu Sans",Arial,sans-serif;color:#1a1f2b;margin:0}}
h1{{font-size:20pt;margin:0 0 2px;color:#0d1b2a}}
.sub{{color:#5a6472;font-size:9.5pt;margin-bottom:14px}}
h2{{font-size:12.5pt;margin:20px 0 6px;padding-bottom:3px;border-bottom:2px solid #e2e6ec;color:#0d1b2a}}
table{{border-collapse:collapse;width:100%;font-size:9.5pt;margin:6px 0}}
th,td{{border:1px solid #d3d8e0;padding:5px 7px;text-align:left;vertical-align:top}}
th{{background:#eef1f5;font-weight:600}}
code{{font-family:"DejaVu Sans Mono",monospace;font-size:9pt;background:#f2f4f7;padding:1px 4px;border-radius:3px}}
.card{{border:1px solid #dfe3ea;border-left-width:5px;border-radius:5px;padding:9px 12px;margin:9px 0;page-break-inside:avoid}}
.p1{{border-left-color:#c0392b}}.p2{{border-left-color:#e08e0b}}.p3{{border-left-color:#2e7dd1}}.lo{{border-left-color:#7a8494}}
.card h3{{margin:0 0 4px;font-size:11pt}}
.badge{{display:inline-block;font-size:8pt;font-weight:700;color:#fff;padding:1px 7px;border-radius:10px;margin-right:6px;vertical-align:1px}}
.b1{{background:#c0392b}}.b2{{background:#e08e0b}}.b3{{background:#2e7dd1}}.blo{{background:#7a8494}}
.card p{{margin:4px 0;font-size:10pt}}
.ok{{color:#1e7d3c;font-weight:600}} .warn{{color:#c0392b;font-weight:600}}
.grid{{display:flex;gap:10px;margin:8px 0}}
.stat{{flex:1;border:1px solid #dfe3ea;border-radius:5px;padding:8px 10px;text-align:center}}
.stat .n{{font-size:17pt;font-weight:700;color:#0d1b2a}}
.stat .l{{font-size:8pt;color:#5a6472;text-transform:uppercase;letter-spacing:.4px}}
.two{{display:flex;gap:14px}} .two>div{{flex:1}}
.foot{{margin-top:22px;padding-top:8px;border-top:1px solid #e2e6ec;font-size:8.5pt;color:#7a8494}}
</style></head><body>
<h1>Wazuh Weekly Security Review</h1>
<div class="sub">Host <b>{esc(d.get('host','wazuh-manager'))}</b> · window {d.get('window_days',7)} days ·
generated {esc(d.get('generated',''))} · cluster <span class="{cl_class}">{esc(cl_line)}</span></div>

<div class="grid">
<div class="stat"><div class="n">{d.get('total',0):,}</div><div class="l">Alerts / 7d</div></div>
<div class="stat"><div class="n">{n_l10}</div><div class="l">Level 10</div></div>
<div class="stat"><div class="n">{n_l9}</div><div class="l">Level 9</div></div>
<div class="stat"><div class="n">{up}/{len(agents)}</div><div class="l">Agents active</div></div>
</div>

<h2>Auto-flagged findings</h2>
{cards_html or '<p class="ok">Nothing flagged this period.</p>'}

{l9_html}

<div class="two">
<div><h2>Alerts by level</h2><table><tr><th>Level</th><th>Count</th></tr>{lvl_rows}</table></div>
<div><h2>Ingestion {ing_note}</h2><table><tr><th>Date</th><th>Alerts</th></tr>{tl_rows}</table></div>
</div>

<div class="foot">Automated · queried read-only via indexer :9200 · levels 3=low 5–7=med 9–10=high ·
CisoDiagonal SOC</div>
</body></html>"""

open(out, "w").write(HTML)
print(out)
