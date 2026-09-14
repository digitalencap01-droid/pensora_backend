import re

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationService:
    @staticmethod
    def validate_row(row_dict: dict) -> tuple[bool, list[str]]:
        errors = []
        email = row_dict.get("email")
        phone = row_dict.get("phone")
        first_name = row_dict.get("first_name")
        full_name = row_dict.get("full_name")

        if email and not EMAIL_REGEX.match(email):
            errors.append(f"Invalid email format: '{email}'")

        if not email and not phone and not first_name and not full_name:
            errors.append("Row contains no identifiable contact info (missing email, phone, or name)")

        is_valid = len(errors) == 0
        return is_valid, errors
