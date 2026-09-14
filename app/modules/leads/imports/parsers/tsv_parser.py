from app.modules.leads.imports.parsers.csv_parser import CSVParser


class TSVParser(CSVParser):
    def parse(self, file_bytes: bytes, sheet_name: str | None = None) -> dict:
        text = self._decode_bytes(file_bytes)
        # Force tab delimiter for TSV
        import csv
        import io

        f = io.StringIO(text.strip())
        reader = csv.reader(f, delimiter="\t")

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
