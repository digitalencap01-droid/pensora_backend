import json
from app.modules.leads.imports.parsers.base import BaseParser


class JSONParser(BaseParser):
    def parse(self, file_bytes: bytes, sheet_name: str | None = None) -> dict:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        data = json.loads(text)

        if isinstance(data, dict):
            # If nested object like {"data": [...]} or {"leads": [...]}
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    data = val
                    break

        if not isinstance(data, list):
            data = [data] if isinstance(data, dict) else []

        headers = list({k for row in data if isinstance(row, dict) for k in row.keys()})
        rows = [
            {k: str(row.get(k, "")).strip() for k in headers}
            for row in data
            if isinstance(row, dict)
        ]

        return {
            "headers": headers,
            "rows": rows,
            "sheets": [{"name": "Default", "rows": len(rows)}],
            "selected_sheet": "Default",
        }
