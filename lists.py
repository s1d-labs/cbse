"""Task `lists` (project cbse-lists): one queue item per state. Fetches the state's whole school list from SARAS (one POST
returns every school of the state), stores the raw page in the bucket and one record per school (id = affiliation number)."""
import gzip
import os
import time

from scrape_hub_client import HubClient

import saras

PROJECT = os.environ["SCRAPE_POOL_PROJECT"]
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300


def main():
    hub = HubClient(PROJECT, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    s = saras.session()
    try:
        while time.time() < DEADLINE:
            if hub.settings.get("paused"):
                time.sleep(30); continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break
            item = items[0]
            state = item["payload"]["state"]
            form = saras.fetch(hub, s, saras.LIST_URL)
            page = form and saras.fetch(hub, s, saras.LIST_URL, data={
                "__RequestVerificationToken": saras.token(form), "MainRadioValue": "State_wise", "State": state, "District": "",
                "Region": "", "InstName_orAddress": "", "RegiAffNo": "", "__Invariant": "RegiAffNo", "SchoolStatusWise": "0"})
            if not page:
                hub.complete([item["key"]], "failed", error="list did not load"); continue
            rows = saras.parse_list(page)
            if not rows and "AfflicationDetails" in page:
                hub.complete([item["key"]], "failed", error="list layout changed: no rows parsed"); continue
            hub.upload_many([(f"lists/{item['key']}.html.gz", gzip.compress(page.encode()), "application/gzip")])
            for aff, row in rows:
                hub.record(aff, {**row, "state_code": state})
            hub.complete([item["key"]], "done", fetched=len(rows))
            time.sleep(max(3.0, hub.settings.get("delay_ms", 0) / 1000))
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200]); raise


if __name__ == "__main__":
    main()
