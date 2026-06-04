import re
from typing import Dict, List, Optional, Tuple


class SensitiveDataProtection:
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    DATA_CLASSIFICATIONS = {
        "public": {"risk_level": 0, "encryption_required": False, "access_control": False},
        "internal": {"risk_level": 1, "encryption_required": False, "access_control": True},
        "confidential": {"risk_level": 2, "encryption_required": True, "access_control": True},
        "restricted": {"risk_level": 3, "encryption_required": True, "access_control": True},
    }

    def scan_for_pii(self, text: str) -> Dict[str, List[str]]:
        found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found[pii_type] = matches
        return found

    def redact_pii(self, text: str, pii_types: Optional[List[str]] = None) -> str:
        if pii_types is None:
            pii_types = list(self.PII_PATTERNS.keys())
        for pii_type in pii_types:
            if pii_type in self.PII_PATTERNS:
                text = re.sub(self.PII_PATTERNS[pii_type], f"[REDACTED_{pii_type.upper()}]", text)
        return text

    def encrypt_sensitive_fields(self, data: Dict, sensitive_fields: List[str], encrypt_func) -> Dict:
        result = dict(data)
        for field in sensitive_fields:
            if field in result and isinstance(result[field], str):
                result[field] = encrypt_func(result[field].encode())
        return result

    def check_data_classification(self, data: Dict, required_classification: str = "confidential") -> Tuple[bool, List[str]]:
        issues = []
        req = self.DATA_CLASSIFICATIONS.get(required_classification, self.DATA_CLASSIFICATIONS["confidential"])
        pii_found = {}
        for key, value in data.items():
            if isinstance(value, str):
                found = self.scan_for_pii(value)
                if found:
                    pii_found[key] = found
        if pii_found and not req["encryption_required"]:
            issues.append("PII detected but encryption not required for this classification")
        if pii_found and not req["access_control"]:
            issues.append("PII detected but access control not enforced")
        return len(issues) == 0, issues

    def mask_pii_in_dict(self, data: Dict, fields_to_mask: Optional[List[str]] = None) -> Dict:
        result = dict(data)
        for key, value in result.items():
            if fields_to_mask and key not in fields_to_mask:
                continue
            if isinstance(value, str):
                for pii_type, pattern in self.PII_PATTERNS.items():
                    value = re.sub(pattern, f"[MASKED_{pii_type.upper()}]", value)
                result[key] = value
        return result

    def detect_sensitive_headers(self, headers: Dict[str, str]) -> List[str]:
        sensitive = []
        for key, value in headers.items():
            lower_key = key.lower()
            if any(s in lower_key for s in ["auth", "token", "key", "secret", "password"]):
                sensitive.append(key)
            for pii_type, pattern in self.PII_PATTERNS.items():
                if re.search(pattern, value):
                    sensitive.append(f"{key} (contains {pii_type})")
        return sensitive

    def get_classification_requirements(self, classification: str) -> Dict:
        return self.DATA_CLASSIFICATIONS.get(classification, self.DATA_CLASSIFICATIONS["confidential"])
