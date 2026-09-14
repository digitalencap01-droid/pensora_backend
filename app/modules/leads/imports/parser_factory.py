from app.modules.leads.imports.parsers.base import BaseParser
from app.modules.leads.imports.parsers.csv_parser import CSVParser
from app.modules.leads.imports.parsers.excel_parser import ExcelParser
from app.modules.leads.imports.parsers.json_parser import JSONParser
from app.modules.leads.imports.parsers.tsv_parser import TSVParser


class ParserFactory:
    @staticmethod
    def get(detected_type: str) -> BaseParser:
        if detected_type in ["xlsx", "xls"]:
            return ExcelParser()
        elif detected_type == "json":
            return JSONParser()
        elif detected_type == "tsv":
            return TSVParser()
        else:
            return CSVParser()
