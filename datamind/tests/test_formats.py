from pathlib import Path

import pytest

from datamind.capabilities.ingest.formats import extract_document, extract_tabular


def test_extract_json_and_html_to_text(tmp_path: Path):
    payload = tmp_path / "payload.json"
    payload.write_text('{"name":"Ada","items":[1,2]}', encoding="utf-8")
    result = extract_document(payload)
    assert result.format == "json"
    assert '"name": "Ada"' in result.text

    page = tmp_path / "page.html"
    page.write_text("<h1>Report</h1><p>Total: 42</p>", encoding="utf-8")
    result = extract_document(page)
    assert result.text == "Report\nTotal: 42"


def test_extract_xlsx_returns_one_table_per_sheet(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    first = workbook.active
    first.title = "Orders"
    first.append(["item", "cost"])
    first.append(["A", 10])
    second = workbook.create_sheet("Returns")
    second.append(["item", "reason"])
    second.append(["B", "damaged"])
    path = tmp_path / "workbook.xlsx"
    workbook.save(path)

    tables = extract_tabular(path)
    assert [table[0] for table in tables] == ["Orders", "Returns"]
    assert tables[0][2][0] == {"item": "A", "cost": 10}


def test_pdf_prefers_mineru_and_falls_back_to_pypdf(tmp_path: Path, monkeypatch):
    from datamind.capabilities.ingest import formats
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"placeholder")
    monkeypatch.delenv("DATAMIND_MINERU", raising=False)
    monkeypatch.setattr(formats, "_mineru_text", lambda path: ("# MinerU", [{"type": "markdown"}]))
    result = extract_document(pdf)
    assert result.text == "# MinerU"
    assert "parsed with MinerU" in result.warnings

    monkeypatch.setattr(formats, "_mineru_text", lambda path: (_ for _ in ()).throw(RuntimeError("missing")))
    monkeypatch.setattr(formats, "_pdf_text", lambda path: ("fallback", [{"type": "page", "page": 1}]))
    result = extract_document(pdf)
    assert result.text == "fallback"
    assert any("fell back to pypdf" in warning for warning in result.warnings)
