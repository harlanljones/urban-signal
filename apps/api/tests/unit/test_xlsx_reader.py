"""The streaming .xlsx reader: shared strings, cell types, date styles, and
the zip layout Excel writes (Richmond's assessor workbook, 2026-09-30)."""

import io
import zipfile
from datetime import datetime

import pytest

from src.producers.xlsx_reader import (
    _column,
    _is_date_format,
    is_xlsx,
    iter_xlsx_rows,
    serial_to_datetime,
)

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# cellXfs: 0 General, 1 built-in m/d/yyyy, 2 custom date and time, 3 custom
# number.
STYLES = f"""<styleSheet xmlns="{MAIN}">
<numFmts count="2"><numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd hh:mm"/>
<numFmt numFmtId="165" formatCode="&quot;$&quot;#,##0.00"/></numFmts>
<cellXfs count="4"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="164"/><xf numFmtId="165"/></cellXfs>
</styleSheet>"""


def _workbook(
    rows_xml: str,
    strings: list[str] | None = None,
    *,
    date1904: bool = False,
    sheet_target: str = "worksheets/sheet1.xml",
    strings_xml: str | None = None,
) -> io.BytesIO:
    """An .xlsx in memory: one worksheet, optional shared strings and styles."""
    props = '<workbookPr date1904="1"/>' if date1904 else "<workbookPr/>"
    workbook = (
        f'<workbook xmlns="{MAIN}" xmlns:r="{DOC_REL}">{props}'
        '<sheets><sheet name="TRANSFERS" sheetId="2" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        f'<Relationships xmlns="{PKG_REL}">'
        f'<Relationship Id="rId3" Type="{REL_TYPE}/styles" Target="styles.xml"/>'
        f'<Relationship Id="rId1" Type="{REL_TYPE}/worksheet" Target="{sheet_target}"/>'
        f'<Relationship Id="rId4" Type="{REL_TYPE}/sharedStrings" Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    sheet = f'<worksheet xmlns="{MAIN}"><sheetData>{rows_xml}</sheetData></worksheet>'
    if strings_xml is None:
        items = "".join(f"<si><t>{text}</t></si>" for text in strings or [])
        strings_xml = f'<sst xmlns="{MAIN}" count="{len(strings or [])}">{items}</sst>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/" + sheet_target.lstrip("/").removeprefix("xl/"), sheet)
        archive.writestr("xl/styles.xml", STYLES)
        archive.writestr("xl/sharedStrings.xml", strings_xml)
    buf.seek(0)
    return buf


HEADER = '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'


def test_rows_are_keyed_by_the_header_and_typed():
    rows = (
        HEADER
        + '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" s="1"><v>46287</v></c><c r="C2"><v>160000</v></c></row>'
        + '<row r="3"><c r="A3" t="s"><v>4</v></c><c r="B3" s="2"><v>46287.5</v></c><c r="C3"><v>0.25750000000000001</v></c></row>'
    )
    book = _workbook(rows, ["PIN", "TRANSFER_DATE", "CONSIDERATION", "N0000812012", "E0001234005"])

    assert list(iter_xlsx_rows(book)) == [
        {"PIN": "N0000812012", "TRANSFER_DATE": datetime.fromisoformat("2026-09-22"), "CONSIDERATION": 160000},
        {"PIN": "E0001234005", "TRANSFER_DATE": datetime.fromisoformat("2026-09-22T12:00"), "CONSIDERATION": 0.2575},
    ]


def test_skipped_cells_read_as_none_and_empty_rows_are_dropped():
    rows = (
        HEADER
        + '<row r="2"><c r="C2"><v>7</v></c></row>'
        + '<row r="3"></row>'
        + '<row r="4"><c r="A4" t="s"><v>3</v></c><c r="B4" t="s"><v>5</v></c></row>'
    )
    book = _workbook(rows, ["PIN", "TRANSFER_DATE", "CONSIDERATION", "N0000812012", "unused", ""])

    assert list(iter_xlsx_rows(book)) == [
        {"PIN": None, "TRANSFER_DATE": None, "CONSIDERATION": 7},
        {"PIN": "N0000812012", "TRANSFER_DATE": None, "CONSIDERATION": None},
    ]


def test_cells_without_references_take_the_next_column():
    rows = (
        '<row><c t="inlineStr"><is><t>a</t></is></c><c t="inlineStr"><is><t>b</t></is></c></row>'
        '<row><c><v>1</v></c><c><v>2</v></c></row>'
    )
    assert list(iter_xlsx_rows(_workbook(rows))) == [{"a": 1, "b": 2}]


def test_the_first_row_with_a_value_is_the_header():
    rows = '<row r="1"></row><row r="2"><c r="B2" t="inlineStr"><is><t>PIN</t></is></c></row>' \
        '<row r="3"><c r="B3" t="inlineStr"><is><t>W0001</t></is></c></row>'
    assert list(iter_xlsx_rows(_workbook(rows))) == [{"PIN": "W0001"}]


def test_other_cell_types():
    rows = (
        '<row r="1"><c r="A1" t="inlineStr"><is><t>flag</t></is></c><c r="B1" t="inlineStr"><is><t>err</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t>formula</t></is></c><c r="D1" t="inlineStr"><is><t>iso</t></is></c>'
        '<c r="E1" t="inlineStr"><is><t>money</t></is></c></row>'
        '<row r="2"><c r="A2" t="b"><v>1</v></c><c r="B2" t="e"><v>#N/A</v></c>'
        '<c r="C2" t="str"><f>A1&amp;"x"</f><v>flagx</v></c><c r="D2" t="d"><v>2026-09-22T00:00:00</v></c>'
        '<c r="E2" s="3"><v>1250.5</v></c></row>'
    )
    assert list(iter_xlsx_rows(_workbook(rows))) == [
        {"flag": True, "err": None, "formula": "flagx", "iso": "2026-09-22T00:00:00", "money": 1250.5}
    ]


def test_rich_text_joins_its_runs_and_skips_phonetic_text():
    strings_xml = (
        f'<sst xmlns="{MAIN}"><si><t>NAME</t></si>'
        "<si><r><rPr><b/></rPr><t>MAIN </t></r><r><t>ST</t></r><rPh><t>ignored</t></rPh></si></sst>"
    )
    rows = '<row r="1"><c r="A1" t="s"><v>0</v></c></row><row r="2"><c r="A2" t="s"><v>1</v></c></row>'
    assert list(iter_xlsx_rows(_workbook(rows, strings_xml=strings_xml))) == [{"NAME": "MAIN ST"}]


def test_a_1904_workbook_counts_from_1904():
    rows = '<row r="1"><c r="A1" t="inlineStr"><is><t>d</t></is></c></row><row r="2"><c r="A2" s="1"><v>0</v></c></row>'
    assert list(iter_xlsx_rows(_workbook(rows, date1904=True))) == [{"d": datetime.fromisoformat("1904-01-01")}]


def test_headers_can_be_renamed():
    rows = HEADER + '<row r="2"><c r="C2"><v>5</v></c></row>'
    book = _workbook(rows, ["Parcel ID", "Transfer Date", "CONSIDERATION"])
    assert list(iter_xlsx_rows(book, rename=str.lower)) == [
        {"parcel id": None, "transfer date": None, "consideration": 5}
    ]


def test_an_absolute_sheet_target_resolves():
    rows = '<row r="1"><c r="A1" t="inlineStr"><is><t>k</t></is></c></row><row r="2"><c r="A2"><v>3</v></c></row>'
    book = _workbook(rows, sheet_target="/xl/worksheets/sheet7.xml")
    assert list(iter_xlsx_rows(book)) == [{"k": 3}]


def test_long_integers_stay_exact():
    rows = '<row r="1"><c r="A1" t="inlineStr"><is><t>n</t></is></c></row><row r="2"><c r="A2"><v>202609290000001</v></c></row>'
    assert list(iter_xlsx_rows(_workbook(rows))) == [{"n": 202609290000001}]


@pytest.mark.parametrize(
    ("serial", "expected"),
    [
        (1, datetime.fromisoformat("1900-01-01")),
        (59, datetime.fromisoformat("1900-02-28")),
        (61, datetime.fromisoformat("1900-03-01")),
        (46287, datetime.fromisoformat("2026-09-22")),
        (46287.75, datetime.fromisoformat("2026-09-22T18:00")),
    ],
)
def test_serials_follow_excels_1900_calendar(serial, expected):
    assert serial_to_datetime(serial) == expected


@pytest.mark.parametrize(
    ("code", "is_date"),
    [
        ("[$-409]m/d/yy h:mm AM/PM", True),
        ("yyyy\\-mm\\-dd", True),
        ("[h]:mm:ss", True),
        ('"Total "0.00', False),
        ("General", False),
        ("#,##0", False),
        ("[Red]0.00", False),
    ],
)
def test_custom_formats_that_show_dates(code, is_date):
    assert _is_date_format(code) is is_date


def test_column_letters():
    assert [_column(ref) for ref in ("A1", "Z9", "AA10", "AB439399")] == [0, 25, 26, 27]


def test_is_xlsx_reads_the_zip_signature():
    assert is_xlsx(_workbook("").getvalue())
    assert not is_xlsx(b"\xd0\xcf\x11\xe0legacy xls")
