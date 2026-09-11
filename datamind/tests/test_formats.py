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
