"""What this family scrapes: the CBSE affiliation directory, SARAS (saras.cbse.gov.in).

- cbse-lists: one item per state; each returns the state's whole list of affiliated schools.
- cbse-schools: the affiliation numbers (data/aff-nos.json, made from the lists), 25 per item; one detail page each
  (affiliation period, level, school type, trust/society, PIN code, year founded).
To pick up new schools: run cbse-lists again, rebuild data/aff-nos.json from its records, run Setup (existing keys stay).

Pacing: SARAS refused some requests (403) at about 1.3 requests a second from one client, so this stays well below:
at most 2 workers, one request at a time each, 1.5 s apart (about 0.9 a second in total).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
FAMILY = json.loads((HERE / "scrape.json").read_text())["family"]
STATES = json.loads((HERE / "data/states.json").read_text())
AFF = json.loads((HERE / "data/aff-nos.json").read_text())
BATCH = 25
TARGET = "saras.cbse.gov.in"

PROJECTS = [
    {
        "name": f"{FAMILY}-lists",
        "title": "CBSE school lists, one per state (SARAS)",
        "task": "lists",
        "unit_label": "state", "record_label": "school",
        "pool": {"max_workers": 1, "threads": 1, "delay_ms": 3000},
        "items": [{"key": f"state-{s['code']}", "payload": {"state": s["code"], "name": s["name"]}} for s in STATES],
        "expected_records": len(AFF),
    },
    {
        "name": f"{FAMILY}-schools",
        "title": "CBSE school affiliation details (SARAS)",
        "task": "details",
        "unit_label": "batch of 25 schools", "record_label": "school",
        "pool": {"max_workers": 2, "threads": 1, "delay_ms": 1500},
        "items": [{"key": f"aff-{AFF[i]}", "payload": {"aff": AFF[i:i + BATCH], "expected": len(AFF[i:i + BATCH])}}
                  for i in range(0, len(AFF), BATCH)],
        "expected_records": len(AFF),
    },
]

# No health check: the hub's probe would fail on SARAS's incomplete TLS chain (see saras.py) and hold the work.
# The hub's automatic back-off on 403/429/503 does the protecting instead.
PROBES = []
