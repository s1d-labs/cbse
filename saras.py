"""Shared code for the cbse family: fetching from SARAS (saras.cbse.gov.in) and the two pure parsers.

TLS: the site's certificate chain lacks its intermediate (Sectigo Public Server Authentication CA DV R36). The file
sectigo-dv-r36.pem (from crt.sectigo.com) is added to certifi's roots, so certificates are still verified.

Terms: CBSE's website policy allows free reproduction if the material is reproduced accurately and the source is
acknowledged prominently; it asks for permission before other sites hyperlink to CBSE pages.
"""
import html
import os
import re
import tempfile
import time

import certifi
import requests

BASE = "https://saras.cbse.gov.in"
LIST_URL = BASE + "/SARAS/AffiliatedList/ListOfSchdirReport"
DETAIL_URL = BASE + "/SARAS/AffiliatedList/AfflicationDetails/{}"
UA = "Mozilla/5.0 (compatible; s1d-labs/cbse school directory; +https://github.com/s1d-labs/cbse)"


def session():
    bundle = os.path.join(tempfile.gettempdir(), "cbse-ca-bundle.pem")
    with open(bundle, "w") as f:
        f.write(open(certifi.where()).read())
        f.write(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sectigo-dv-r36.pem")).read())
    s = requests.Session()
    s.verify = bundle
    s.headers.update({"User-Agent": UA, "Referer": LIST_URL})
    return s


def fetch(hub, s, url, data=None, timeout=120):
    """One request with the metrics the hub reads. Returns the page text, or None (counted as error or block)."""
    t = time.time()
    try:
        r = s.post(url, data=data, timeout=timeout) if data is not None else s.get(url, timeout=timeout)
    except requests.RequestException:
        hub.metric("http_error"); hub.error()
        return None
    hub.metric("n_http"); hub.metric("t_http_s", time.time() - t)
    if r.status_code != 200:
        hub.metric(f"http_{r.status_code}")
        if r.status_code in (403, 429, 503):
            hub.block()
        return None
    r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else "utf-8"
    return r.text


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def states(form_page):
    """[(code, name)] from the directory form's State select."""
    sel = re.search(r'<select[^>]*name="State"[^>]*>(.*?)</select>', form_page, re.S).group(1)
    return [(v, html.unescape(n).strip()) for v, n in re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]*)', sel)]


def token(form_page):
    return re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', form_page).group(1)


def parse_list(page):
    """State list page -> [(aff_no, row)]: affiliation and school code, state, district, level, name, principal,
    address, website."""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        m = re.search(r"AfflicationDetails/(\d+)", tr)
        if not m:
            continue
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        joined = " | ".join(cells)
        pick = lambda rx: (re.search(rx, joined) or [None, ""])[1].strip()
        out.append((m.group(1), {
            "aff_no": m.group(1),
            "school_code": pick(r"Sch\. Code\s*:\s*(\S+)"),
            "state": pick(r"State\s*:\s*(.*?)\s*District\s*:"),
            "district": pick(r"District\s*:\s*([^|]*)"),
            "level": cells[3] if len(cells) > 3 else "",
            "name": pick(r"Name\s*:\s*(.*?)\s*Head/Principal Name"),
            "principal": pick(r"Head/Principal Name\s*:\s*([^|]*)"),
            "address": pick(r"Address\s*:\s*(.*?)(?:\s*Website\s*:|\||$)"),
            "website": pick(r"Website\s*:\s*([^|]*)"),
        }))
    return out


# Every field on the page (public data, owner 2026-11-11), including the principal's details.
DETAIL_LABELS = {
    "Name of Institution": "name", "Affiliation Number": "aff_no", "State": "state", "District": "district",
    "Postal Address": "address", "Pin Code": "pincode", "Website": "website", "Year of Foundation": "founded",
    "Date of First Opening of School": "first_opened", "Name of Principal/ Head of Institution": "principal",
    "Status of The School": "level", "School Type": "school_type", "Name of Trust/ Society/ Managing Committee": "society",
    "Gender": "principal_gender", "Principal's Educational/Professional Qualifications:": "principal_qualifications",
    "Administrative:": "principal_admin_years", "Teaching:": "principal_teaching_years",
    "Type of affiliation": "affiliation_type", "Remarks, if any": "remarks",
}


def parse_detail(page):
    """Detail page -> dict of DETAIL_LABELS fields + affiliated_from / affiliated_to (dd/mm/yyyy). {} for an empty page."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    cells = [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", body, re.S)]
    out = {}
    for i, c in enumerate(cells[:-1]):
        key = DETAIL_LABELS.get(c)
        nxt = cells[i + 1]
        if key and key not in out and nxt and nxt not in DETAIL_LABELS and not nxt.startswith(("No of Experience", "From :")):
            out[key] = nxt
    m = re.search(r"From\s*:\s*(\d{2}/\d{2}/\d{4}).*?To\s*:\s*(\d{2}/\d{2}/\d{4})", " ".join(cells))
    if m:
        out["affiliated_from"], out["affiliated_to"] = m.group(1), m.group(2)
    return out
