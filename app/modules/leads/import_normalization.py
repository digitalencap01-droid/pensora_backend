import re


class NormalizationService:
    @staticmethod
    def normalize_email(email_raw: str | None) -> str | None:
        if not email_raw:
            return None
        cleaned = email_raw.strip().lower()
        if "@" in cleaned and "." in cleaned:
            return cleaned
        return None

    @staticmethod
    def normalize_phone(phone_raw: str | None) -> str | None:
        if not phone_raw:
            return None
        cleaned = re.sub(r"[^\d+]", "", str(phone_raw).strip())
        if len(cleaned) >= 7:
            return cleaned
        return None

    @staticmethod
    def normalize_name(name_raw: str | None) -> str | None:
        if not name_raw:
            return None
        cleaned = " ".join(str(name_raw).strip().split())
        return cleaned.title() if cleaned else None

    @staticmethod
    def normalize_value(val: str | None) -> str | None:
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None
