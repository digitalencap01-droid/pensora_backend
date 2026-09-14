from app.db.models.leads import Lead


class DeduplicationService:
    @staticmethod
    def identify_duplicate(
        existing_leads: list[Lead], new_lead_data: dict
    ) -> Lead | None:
        email = new_lead_data.get("email")
        if email:
            for lead in existing_leads:
                if lead.email and lead.email.lower() == email.lower():
                    return lead

        phone = new_lead_data.get("phone")
        if phone:
            for lead in existing_leads:
                if lead.phone and lead.phone == phone:
                    return lead

        return None
