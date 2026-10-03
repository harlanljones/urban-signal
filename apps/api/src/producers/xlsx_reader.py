"""Read an .xlsx worksheet one row at a time, with the standard library.

An .xlsx workbook is a zip of XML parts. Richmond's assessor publishes every
recorded property transfer as one 72 MB workbook whose worksheet XML runs to
400 MB, so a reader that builds the sheet in memory (pandas, or openpyxl
outside read-only mode) holds gigabytes, and xlrd no longer opens .xlsx at
all. This reader walks the first worksheet with ``iterparse``, dropping each
row once it is read, and keeps the shared-string table as one UTF-8 buffer.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
from array import array
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from typing import IO, Any
from xml.etree.ElementTree import Element, fromstring, iterparse

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_ROW, _CELL, _VALUE, _INLINE = f"{_MAIN}row", f"{_MAIN}c", f"{_MAIN}v", f"{_MAIN}is"
_DIGITS = "0123456789"

# Built-in number formats that show a serial number as a date or a time
# (ECMA-376 Part 1, 18.8.30).
_BUILTIN_DATE_FORMATS = frozenset({14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47})
# What a custom format prints literally: quoted text, escaped characters, and
# bracketed colours or locales.
_FORMAT_LITERALS = re.compile(r'"[^"]*"|\\.|\[[^\]]*\]')
_INTEGER = re.compile(r"-?\d+")
# A serial counts days on the workbook's own calendar and carries no zone, so
# the dates it makes are naive. Excel's 1900 calendar counts a 29 February 1900
# that never was, so serials below 61 count from a day later.
_EPOCH_1900 = datetime.fromisoformat("1899-12-30")
_EPOCH_1900_EARLY = datetime.fromisoformat("1899-12-31")
_EPOCH_1904 = datetime.fromisoformat("1904-01-01")


def is_xlsx(head: bytes) -> bool:
    """Whether a file's first bytes open a zip archive, as every .xlsx does."""
    return head[:4] == b"PK\x03\x04"


class _StringTable:
    """A workbook's shared strings as one UTF-8 buffer and each string's end."""

    def __init__(self) -> None:
        self._text = bytearray()
        self._ends = array("q")

    def append(self, value: str) -> None:
        self._text += value.encode("utf-8")
        self._ends.append(len(self._text))

    def __getitem__(self, index: int) -> str:
        start = self._ends[index - 1] if index > 0 else 0
        return self._text[start : self._ends[index]].decode("utf-8")

    def __len__(self) -> int:
        return len(self._ends)


def _text_of(item: Element) -> str:
    """A string item's text: its ``<t>``, or its rich-text runs' (phonetic runs aside)."""
    plain = item.find(f"{_MAIN}t")
    if plain is not None:
        return plain.text or ""
    return "".join(run.findtext(f"{_MAIN}t") or "" for run in item.iterfind(f"{_MAIN}r"))


def _read_strings(archive: zipfile.ZipFile, path: str | None) -> _StringTable:
    table = _StringTable()
    if path is None:
        return table
    with archive.open(path) as fh:
        root = None
        for event, element in iterparse(fh, events=("start", "end")):
            if event == "start":
                if root is None:
                    root = element
            elif element.tag == f"{_MAIN}si":
                table.append(_text_of(element))
                root.clear()
    return table


def _is_date_format(code: str) -> bool:
    """Whether a custom number format shows a date or a time."""
    return any(ch in "ymdhs" for ch in _FORMAT_LITERALS.sub("", code).lower())


def _date_styles(archive: zipfile.ZipFile, path: str | None) -> frozenset[str]:
    """The cell style indexes whose number format shows a date or a time, as
    the ``s`` attribute spells them."""
    if path is None:
        return frozenset()
    root = fromstring(archive.read(path))
    custom = {
        int(fmt.get("numFmtId", "0")): fmt.get("formatCode", "")
        for fmt in root.iterfind(f"{_MAIN}numFmts/{_MAIN}numFmt")
    }
    dates = set()
    for index, xf in enumerate(root.iterfind(f"{_MAIN}cellXfs/{_MAIN}xf")):
        fmt = int(xf.get("numFmtId", "0"))
        if fmt in _BUILTIN_DATE_FORMATS or (fmt in custom and _is_date_format(custom[fmt])):
            dates.add(str(index))
    return frozenset(dates)


def serial_to_datetime(serial: float, date1904: bool = False) -> datetime:
    """A spreadsheet date serial as a naive datetime, to the second."""
    if date1904:
        epoch = _EPOCH_1904
    else:
        epoch = _EPOCH_1900_EARLY if serial < 61 else _EPOCH_1900
    return epoch + timedelta(seconds=round(serial * 86400))


def _column(ref: str) -> int:
    """The zero-based column of a cell reference such as ``AB12``."""
    index = 0
    for ch in ref:
        if not "A" <= ch <= "Z":
            break
        index = index * 26 + ord(ch) - 64
    return index - 1


def _parts(archive: zipfile.ZipFile) -> tuple[str, str | None, str | None, bool]:
    """The first worksheet's path, the shared strings' and styles' paths, and
    whether the workbook counts dates from 1904."""
    workbook = fromstring(archive.read("xl/workbook.xml"))
    sheet = workbook.find(f"{_MAIN}sheets/{_MAIN}sheet")
    if sheet is None:
        raise ValueError("workbook has no worksheet")
    props = workbook.find(f"{_MAIN}workbookPr")
    date1904 = props is not None and props.get("date1904", "0").lower() in ("1", "true")

    targets: dict[str, str] = {}
    by_type: dict[str, str] = {}
    for rel in fromstring(archive.read("xl/_rels/workbook.xml.rels")).iterfind(f"{_PKG_REL}Relationship"):
        target = rel.get("Target", "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        targets[rel.get("Id", "")] = path
        by_type[rel.get("Type", "").rsplit("/", 1)[-1]] = path
    sheet_path = targets[sheet.get(f"{_DOC_REL}id", "")]
    return sheet_path, by_type.get("sharedStrings"), by_type.get("styles"), date1904


def iter_xlsx_rows(
    source: str | IO[bytes],
    rename: Callable[[str], str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield the first worksheet's rows as dicts keyed by its header row.

    The first row with a value is the header; ``rename`` maps each header to
    the key rows use. Empty cells read as None and wholly empty rows are
    skipped. Numbers come back as int or float, cells in a date format as
    naive datetimes, booleans as bool, and error cells (``#N/A``) as None.
    """
    with zipfile.ZipFile(source) as archive:
        sheet_path, strings_path, styles_path, date1904 = _parts(archive)
        strings = _read_strings(archive, strings_path)
        date_styles = _date_styles(archive, styles_path)
        columns: dict[str, int] = {}
        header: list[str] | None = None

        with archive.open(sheet_path) as fh:
            # End events only: a start event per element costs a third more
            # time. Each row is cleared once read; the empty shells left in
            # the tree cost about 90 bytes a row.
            for _, row in iterparse(fh, events=("end",)):
                if row.tag != _ROW:
                    continue
                values: dict[int, Any] = {}
                position = 0
                for cell in row:
                    if cell.tag != _CELL:
                        continue
                    ref = cell.get("r")
                    if ref:
                        letters = ref.rstrip(_DIGITS)
                        position = columns.get(letters, -1)
                        if position < 0:
                            position = columns[letters] = _column(letters)
                    kind = cell.get("t")
                    if kind == "inlineStr":
                        item = cell.find(_INLINE)
                        value: Any = _text_of(item) if item is not None else None
                    else:
                        raw = cell.findtext(_VALUE)
                        if raw is None or raw == "" or kind == "e":
                            value = None
                        elif kind is None or kind == "n":
                            if cell.get("s") in date_styles:
                                value = serial_to_datetime(float(raw), date1904)
                            else:
                                value = int(raw) if _INTEGER.fullmatch(raw) else float(raw)
                        elif kind == "s":
                            value = strings[int(raw)]
                        elif kind == "b":
                            value = raw == "1"
                        else:
                            value = raw
                    if value is not None and value != "":
                        values[position] = value
                    position += 1
                row.clear()
                if not values:
                    continue
                if header is None:
                    names = [str(values.get(i, "")).strip() for i in range(max(values) + 1)]
                    header = [rename(name) if rename else name for name in names]
                    continue
                yield {name: values.get(i) for i, name in enumerate(header) if name}
