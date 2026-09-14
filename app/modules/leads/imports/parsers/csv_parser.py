import csv
import io
from app.modules.leads.imports.parsers.base import BaseParser


class CSVParser(BaseParser):
    def parse(self, file_bytes: bytes, sheet_name: str | None = None) -> dict:
        text = self._decode_bytes(file_bytes)
        delimiter = self._detect_delimiter(text)

        f = io.StringIO(text.strip())
        reader = csv.reader(f, delimiter=delimiter)

        try:
            raw_headers = next(reader)
        except StopIteration:
            return {"headers": [], "rows": [], "sheets": [], "selected_sheet": None}

        headers = [h.strip() for h in raw_headers if h.strip()]
        rows = []

        for row in reader:
            if not row or not any(field.strip() for field in row):
                continue
            row_dict = {
                headers[i]: row[i].strip()
                for i in range(min(len(headers), len(row)))
            }
            rows.append(row_dict)

        return {
            "headers": headers,
            "rows": rows,
            "sheets": [{"name": "Default", "rows": len(rows)}],
            "selected_sheet": "Default",
        }

    @staticmethod
    def _decode_bytes(b: bytes) -> str:
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "windows-1252"]:
            try:
                return b.decode(encoding)
            except (UnicodeDecodeError, AttributeError):
                continue
        return b.decode("utf-8", errors="ignore")

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        sample_line = text.splitlines()[0] if text.splitlines() else ""
        delimiters = [",", ";", "\t", "|"]
        counts = {d: sample_line.count(d) for d in delimiters}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","
