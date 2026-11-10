"""Task `details` (project cbse-schools): one queue item = up to 25 affiliation numbers. Fetches each school's SARAS
detail page one at a time, stores a record per school (id = affiliation number) and the batch's raw pages as one
tar.gz in the bucket. An empty detail page (number not in use any more) is listed as a failure, not a record."""
import io
import os
import tarfile
import time

from scrape_hub_client import HubClient

import saras

PROJECT = os.environ["SCRAPE_POOL_PROJECT"]
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300


def tar_gz(pages):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for aff, page in pages:
            data = page.encode()
            info = tarfile.TarInfo(f"{aff}.html"); info.size = len(data); info.mtime = int(time.time())
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


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
            pages, stored, missed = [], 0, 0
            for aff in item["payload"]["aff"]:
                page = saras.fetch(hub, s, saras.DETAIL_URL.format(aff), timeout=60)
                time.sleep(max(1.0, hub.settings.get("delay_ms", 0) / 1000))
                if page is None:
                    missed += 1; continue
                pages.append((aff, page))
                d = saras.parse_detail(page)
                if d.get("aff_no"):
                    hub.record(aff, d); stored += 1
                else:
                    hub.failure("empty-detail", aff, "detail page has no school (number not in use?)")
            if missed:
                hub.complete([item["key"]], "failed", error=f"{missed} of {len(item['payload']['aff'])} pages did not load"); continue
            hub.upload_many([(f"details/{item['key']}.tar.gz", tar_gz(pages), "application/gzip")])
            hub.complete([item["key"]], "done", fetched=stored)
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200]); raise


if __name__ == "__main__":
    main()
