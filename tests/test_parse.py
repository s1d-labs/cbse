"""Parsers on saved SARAS pages (tests/pages)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saras  # noqa: E402

PAGES = Path(__file__).parent / "pages"


def test_detail():
    d = saras.parse_detail((PAGES / "detail-1000001.html").read_text())
    assert d["aff_no"] == "1000001"
    assert d["pincode"] == "462011"
    assert d["level"] == "Senior Secondary Level"
    assert d["school_type"] == "KV"
    assert d["affiliated_from"] == "01/04/2026" and d["affiliated_to"] == "31/03/2031"
    assert d["principal_gender"] == "Male"
    assert d["principal_qualifications"] == "M SC PHYSICS"
    assert d["principal_admin_years"] == "10" and d["principal_teaching_years"] == "22"
    assert "affiliation_type" not in d  # blank on this page


def test_empty_detail():
    assert saras.parse_detail("<html><table><tr><td>Name of Institution</td><td></td></tr></table></html>") == {}


def test_list():
    rows = saras.parse_list((PAGES / "list-small.html").read_text())
    assert len(rows) == 12
    aff, r = rows[0]
    assert aff == "3200001" and r["state"] == "LAKSHADWEEP" and r["school_code"] == "79902"
    assert r["website"].startswith("https://")
