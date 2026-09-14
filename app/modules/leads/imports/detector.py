import os


class FileFormatDetector:
    @staticmethod
    def detect(filename: str, file_bytes: bytes) -> dict:
        ext = os.path.splitext(filename)[1].lower().strip(".")
        confidence = 0.95

        # Inspect content header magic bytes / strings
        sample = file_bytes[:2048]

        if sample.startswith(b"PK\x03\x04") or ext in ["xlsx", "xlsm", "xltx", "xltm"]:
            return {
                "detected_type": "xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "confidence": 0.99 if sample.startswith(b"PK\x03\x04") else confidence,
            }

        if sample.startswith(b"\xd0\xcf\x11\xe0") or ext == "xls":
            return {
                "detected_type": "xls",
                "mime_type": "application/vnd.ms-excel",
                "confidence": 0.99 if sample.startswith(b"\xd0\xcf\x11\xe0") else confidence,
            }

        decoded_sample = sample.decode("utf-8", errors="ignore").strip()

        if (decoded_sample.startswith("{") or decoded_sample.startswith("[")) or ext == "json":
            return {
                "detected_type": "json",
                "mime_type": "application/json",
                "confidence": 0.95,
            }

        if "\t" in decoded_sample.splitlines()[0] if decoded_sample.splitlines() else False:
            return {
                "detected_type": "tsv",
                "mime_type": "text/tab-separated-values",
                "confidence": 0.90,
            }

        return {
            "detected_type": "csv",
            "mime_type": "text/csv",
            "confidence": 0.90,
        }
