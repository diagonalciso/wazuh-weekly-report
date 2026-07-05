#!/usr/bin/env python3
"""Runs ON the Wazuh server (as root, piped via ssh). Emits JSON week-review data to stdout."""
import json, ssl, subprocess, urllib.request, re
from datetime import datetime, timezone

# admin pw from install-files (never printed)
pw = ""
try:
    out = subprocess.run(
        ["tar", "-O", "-xf", "/home/soc/wazuh-install-files.tar",
         "wazuh-install-files/wazuh-passwords.txt"],
        capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "indexer_password" in ln:
            m = re.search(r"'([^']+)'", ln)
            if m:
                pw = m.group(1); break
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
import base64
auth = base64.b64encode(f"admin:{pw}".encode()).decode()

def q(body):
    req = urllib.request.Request(
        "https://127.0.0.1:9200/wazuh-alerts-*/_search",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.loads(r.read())

rng = {"range": {"@timestamp": {"gte": "now-7d"}}}
data = {"generated": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "window_days": 7}

r = q({"size": 0, "query": rng,
       "aggs": {"lvl": {"terms": {"field": "rule.level", "size": 25, "order": {"_key": "desc"}}}}})
data["total"] = r["hits"]["total"]["value"]
data["by_level"] = [[b["key"], b["doc_count"]] for b in r["aggregations"]["lvl"]["buckets"]]

r = q({"size": 0, "query": {"bool": {"filter": [rng, {"range": {"rule.level": {"gte": 10}}}]}},
       "aggs": {"r": {"terms": {"field": "rule.description", "size": 25}}}})
data["high_total"] = r["hits"]["total"]["value"]
data["high_rules"] = [[b["doc_count"], b["key"]] for b in r["aggregations"]["r"]["buckets"]]

r = q({"size": 0, "query": {"bool": {"filter": [rng, {"term": {"rule.level": 9}}]}},
       "aggs": {"r": {"terms": {"field": "rule.description", "size": 20}}}})
data["l9_rules"] = [[b["doc_count"], b["key"]] for b in r["aggregations"]["r"]["buckets"]]

r = q({"size": 0, "query": {"bool": {"filter": [rng, {"range": {"rule.level": {"gte": 8}}}],
       "should": [{"match": {"rule.groups": "authentication_failed"}},
                  {"match": {"rule.groups": "authentication_failures"}}],
       "minimum_should_match": 1}},
      "aggs": {"ip": {"terms": {"field": "data.srcip", "size": 15}}}})
data["brute_ips"] = [[b["doc_count"], b["key"]] for b in r["aggregations"]["ip"]["buckets"]]

r = q({"size": 0, "query": rng,
       "aggs": {"d": {"date_histogram": {"field": "@timestamp", "calendar_interval": "day"}}}})
data["timeline"] = [[b["key_as_string"][:10], b["doc_count"]] for b in r["aggregations"]["d"]["buckets"]]

# agents
agents = []
try:
    out = subprocess.run(["/var/ossec/bin/agent_control", "-l"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        m = re.search(r"ID:\s*(\d+),\s*Name:\s*([^,]+),.*?(Active|Disconnected|Never connected|Pending)", ln)
        if m:
            agents.append([m.group(1), m.group(2).strip(), m.group(3)])
except Exception:
    pass
data["agents"] = agents

# integration/error signal in ossec.log (last day)
try:
    log = open("/var/ossec/logs/ossec.log", errors="ignore").read().splitlines()
    errs = [l for l in log if "ERROR" in l or "CRITICAL" in l]
    data["iris_errors"] = sum(1 for l in errs if "iris" in l.lower())
    data["error_tail"] = errs[-8:]
except Exception:
    data["iris_errors"] = 0
    data["error_tail"] = []

# cluster health
try:
    req = urllib.request.Request("https://127.0.0.1:9200/_cluster/health",
                                 headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as rr:
        h = json.loads(rr.read())
    data["cluster"] = {"status": h["status"], "nodes": h["number_of_nodes"],
                       "unassigned": h["unassigned_shards"], "active_shards": h["active_shards"]}
except Exception:
    data["cluster"] = {}

print(json.dumps(data))
