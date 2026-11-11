# cbse: CBSE affiliation directory

s1d-labs scrape pool family. Source: **SARAS**, CBSE's affiliation directory (saras.cbse.gov.in), about 33,300 schools.

| Project | Task | Items | Records |
|---|---|---|---|
| `cbse-lists` | `lists.py` | one per state (38) | one per school: affiliation no., school code, state, district, level, name, principal, address, website |
| `cbse-schools` | `details.py` | 25 affiliation numbers each | one per school: every field of the detail page (level, type, trust/society, affiliation period and type, PIN code, year founded, first opened, website, address, principal's name, gender, qualifications, experience, remarks) |

Raw pages go to the family bucket: `cbse-lists/lists/<item>.html.gz`, `cbse-schools/details/<item>.tar.gz`.

- **Every field is kept** (public data): including the principal's name, gender, qualifications and experience,
  type of affiliation and remarks. Records made before 2026-11-11 lack the principal details; the raw pages in the
  bucket have them.
- **Pacing:** SARAS refused some requests at about 1.3 requests a second from one client. The pool runs at most 2 workers,
  one request at a time, 1.5 s apart.
- **TLS:** the site's chain lacks its intermediate certificate; `sectigo-dv-r36.pem` is added to certifi's roots, so
  certificates are still verified. Never turn verification off.
- **Terms:** CBSE allows free reproduction if the material is reproduced accurately and the source is acknowledged
  prominently. It asks for permission before other sites hyperlink to CBSE pages.
- **Used by:** schooldoor.in (matched to UDISE+ schools in the schooldoor repo, `ops/cbse/match.py`).

New schools: run `cbse-lists` again, rebuild `data/aff-nos.json` from its records, then run Setup.
Tests: `python -m pytest tests` (saved pages in `tests/pages`), `scrape-check --items 2 --project cbse-schools`.

The technical contract for the hub and the runner is in `CLAUDE.md`.
