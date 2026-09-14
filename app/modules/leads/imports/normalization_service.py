import re

NULL_STRINGS = {"n/a", "na", "null", "none", "-", "", "undefined"}


class NormalizationService:
    @staticmethod
    def normalize_value(val: str | None) -> str | None:
        if val is None:
            return None
        cleaned = str(val).strip()
        if cleaned.lower() in NULL_STRINGS:
            return None
        return cleaned

    @staticmethod
    def normalize_email(email: str | None) -> str | None:
        cleaned = NormalizationService.normalize_value(email)
        if not cleaned:
            return None
        return cleaned.lower()

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        cleaned = NormalizationService.normalize_value(phone)
        if not cleaned:
            return None
        # Remove spaces, hyphens, parens
        digits = re.sub(r"[^\d+]", "", cleaned)
        if len(digits) == 10 and not digits.startswith("+"):
            return f"+91{digits}"  # Default country code fallback
        elif digits.startswith("0") and len(digits) == 11:
            return f"+91{digits[1:]}"
        return digits

    @staticmethod
    def normalize_name(name: str | None) -> str | None:
        cleaned = NormalizationService.normalize_value(name)
        if not cleaned:
            return None
        # Remove excess spaces
        return re.sub(r"\s+", " ", cleaned).title()
