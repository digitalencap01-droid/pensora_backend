CANONICAL_FIELD_ALIASES = {
    "email": [
        "email", "email address", "email id", "email_id", "mail", "mail id",
        "work email", "e-mail", "contact_email", "mail_address"
    ],
    "phone": [
        "phone", "mobile", "mobile no", "phone number", "contact",
        "contact number", "telephone", "whatsapp number", "cell", "phone_number"
    ],
    "first_name": [
        "first_name", "first name", "firstname", "fname", "given name", "forename"
    ],
    "last_name": [
        "last_name", "last name", "lastname", "lname", "surname", "family name"
    ],
    "full_name": [
        "name", "full name", "full_name", "customer name", "contact name", "lead name"
    ],
    "company_name": [
        "company", "business", "organization", "organisation", "company name",
        "company_name", "employer", "business_name"
    ],
    "job_title": [
        "title", "job_title", "job title", "designation", "role", "position"
    ],
    "status": [
        "status", "lead_status", "stage"
    ],
    "lead_score": [
        "score", "lead_score", "points"
    ],
}


class MappingService:
    @staticmethod
    def auto_map_headers(headers: list[str]) -> dict[str, dict]:
        mappings = {}

        for header in headers:
            normalized = header.lower().strip().replace("-", "_")
            mapped_field = None
            confidence = 0.0

            # 1. Exact match check across all canonical fields
            for target_field, aliases in CANONICAL_FIELD_ALIASES.items():
                if normalized in aliases or header.lower().strip() in aliases:
                    mapped_field = target_field
                    confidence = 0.98
                    break

            # 2. Substring match fallback
            if not mapped_field:
                for target_field, aliases in CANONICAL_FIELD_ALIASES.items():
                    for alias in aliases:
                        if len(alias) > 3 and (alias in normalized or normalized in alias):
                            mapped_field = target_field
                            confidence = 0.85
                            break
                    if mapped_field:
                        break

            if mapped_field:
                mappings[header] = {
                    "suggested_field": mapped_field,
                    "confidence": confidence,
                }
            else:
                mappings[header] = {
                    "suggested_field": f"custom:{header}",
                    "confidence": 0.50,
                }

        return mappings
