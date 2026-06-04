from datetime import datetime, date
from typing import Dict, Optional, Tuple


class AgeGate:
    AGE_REQUIREMENTS = {
        "general": 0,
        "mature": 18,
        "adult": 18,
        "restricted": 21,
        "gambling": 21,
        "alcohol": 21,
        "tobacco": 21,
    }

    CONTENT_CLASSIFICATIONS = {
        "general": {"min_age": 0, "requires_verification": False},
        "mature": {"min_age": 18, "requires_verification": True},
        "adult": {"min_age": 18, "requires_verification": True},
        "explicit": {"min_age": 18, "requires_verification": True},
        "restricted": {"min_age": 21, "requires_verification": True},
    }

    def __init__(self, default_min_age: int = 18):
        self._default_min_age = default_min_age
        self._verification_cache: Dict[str, Dict] = {}

    def verify_age_for_content(self, birth_date: str, content_type: str) -> Dict:
        try:
            if isinstance(birth_date, str):
                bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
            elif isinstance(birth_date, date):
                bd = birth_date
            else:
                return {"verified": False, "error": "Invalid date format"}
        except ValueError:
            return {"verified": False, "error": "Invalid date format"}
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        classification = self.CONTENT_CLASSIFICATIONS.get(
            content_type, {"min_age": self._default_min_age, "requires_verification": True}
        )
        min_age = classification["min_age"]
        verified = age >= min_age
        return {
            "verified": verified,
            "age": age,
            "min_age_required": min_age,
            "content_type": content_type,
            "requires_verification": classification["requires_verification"],
        }

    def check_purchase_eligibility(self, birth_date: str, product_type: str,
                                    is_verified: bool = False) -> Dict:
        try:
            if isinstance(birth_date, str):
                bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
            elif isinstance(birth_date, date):
                bd = birth_date
            else:
                return {"eligible": False, "error": "Invalid date format"}
        except ValueError:
            return {"eligible": False, "error": "Invalid date format"}
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        min_age = self.AGE_REQUIREMENTS.get(product_type, self._default_min_age)
        eligible = age >= min_age
        if not eligible:
            return {
                "eligible": False,
                "age": age,
                "min_age_required": min_age,
                "product_type": product_type,
                "reason": "age_requirement_not_met",
            }
        return {
            "eligible": True,
            "age": age,
            "min_age_required": min_age,
            "product_type": product_type,
            "verification_status": "verified" if is_verified else "pending",
        }

    def get_age_requirements(self) -> Dict:
        return dict(self.AGE_REQUIREMENTS)

    def enforce_age_restriction(self, user_data: Dict, required_type: str) -> Dict:
        birth_date = user_data.get("birth_date")
        if not birth_date:
            return {
                "allowed": False,
                "reason": "no_birth_date",
                "message": "Birth date required for age verification",
            }
        verification = self.verify_age_for_content(birth_date, required_type)
        return {
            "allowed": verification["verified"],
            "age": verification.get("age"),
            "min_age_required": verification.get("min_age_required"),
            "content_type": required_type,
            "message": "Access granted" if verification["verified"] else "Age requirement not met",
        }

    def calculate_age(self, birth_date: str) -> Optional[int]:
        try:
            if isinstance(birth_date, str):
                bd = datetime.strptime(birth_date, "%Y-%m-%d").date()
            elif isinstance(birth_date, date):
                bd = birth_date
            else:
                return None
            today = date.today()
            return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except (ValueError, TypeError):
            return None
