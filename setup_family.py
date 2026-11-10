"""Put this family's projects in the pool. Run by the Setup workflow (GitHub Actions: the hub trusts this repo through
its OIDC token). Safe to run again: queue items that exist are kept."""
from scrape_hub_client import register_project, seed_queue, set_pool, set_probes

from family import FAMILY, PROBES, PROJECTS, TARGET

print("health checks:", set_probes(FAMILY, PROBES))
for p in PROJECTS:
    register_project(p["name"], title=p["title"], unit_label=p["unit_label"], record_label=p["record_label"],
                     expected_units=len(p["items"]), expected_records=p["expected_records"])
    set_pool(p["name"], FAMILY, p["task"], target=TARGET, env={}, probe=None, **p["pool"])
    print(p["name"], "queue:", seed_queue(p["name"], p["items"]))
