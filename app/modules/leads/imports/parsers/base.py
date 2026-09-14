from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_bytes: bytes, sheet_name: str | None = None) -> dict:
        """
        Returns unified dictionary format:
        {
            "headers": ["Name", "Email", ...],
            "rows": [{"Name": "Rahul", "Email": "..."}, ...],
            "sheets": [{"name": "Sheet1", "rows": 100}],
            "selected_sheet": "Sheet1"
        }
        """
        pass
