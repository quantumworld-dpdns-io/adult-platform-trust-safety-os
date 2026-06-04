import re
from typing import Callable, Dict, Optional


class DataMasker:
    def __init__(self, mask_char: str = "*", reveal_start: int = 0, reveal_end: int = 0):
        self._mask_char = mask_char
        self._reveal_start = reveal_start
        self._reveal_end = reveal_end
        self._custom_masks: Dict[str, Callable] = {}

    def _mask_middle(self, value: str, start: int = 2, end: int = 2) -> str:
        if len(value) <= start + end:
            return value
        masked_len = len(value) - start - end
        return value[:start] + self._mask_char * masked_len + value[end:]

    def mask_email(self, email: str) -> str:
        parts = email.split("@")
        if len(parts) != 2:
            return email
        local, domain = parts
        if len(local) <= 2:
            masked_local = local[0] + self._mask_char * 3
        else:
            masked_local = local[0] + self._mask_char * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"

    def mask_phone(self, phone: str) -> str:
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 4:
            return phone
        masked = self._mask_char * (len(digits) - 4) + digits[-4:]
        if len(phone) > len(digits):
            non_digit_count = len(phone) - len(digits)
            return phone[:non_digit_count] + masked
        return masked

    def mask_ssn(self, ssn: str) -> str:
        digits = re.sub(r"\D", "", ssn)
        if len(digits) != 9:
            return ssn
        return f"***-**-{digits[-4:]}"

    def mask_credit_card(self, card: str) -> str:
        digits = re.sub(r"\D", "", card)
        if len(digits) < 8:
            return card
        last_four = digits[-4:]
        masked_middle = self._mask_char * (len(digits) - 8)
        return f"{digits[:4]}-{masked_middle}-{last_four}" if len(digits) == 16 else f"{digits[:4]}{masked_middle}{last_four}"

    def mask_name(self, name: str) -> str:
        parts = name.split()
        if not parts:
            return name
        masked_parts = []
        for i, part in enumerate(parts):
            if i == 0:
                masked_parts.append(part[0] + self._mask_char * (len(part) - 1) if len(part) > 1 else part)
            else:
                masked_parts.append(part[0] + self._mask_char * (len(part) - 1) if len(part) > 1 else part)
        return " ".join(masked_parts)

    def apply_custom_mask(self, value: str, pattern: str, replacement: str) -> str:
        return re.sub(pattern, replacement, value)

    def register_custom_mask(self, name: str, mask_func: Callable) -> None:
        self._custom_masks[name] = mask_func

    def apply_registered_mask(self, name: str, value: str) -> str:
        if name not in self._custom_masks:
            raise ValueError(f"Custom mask '{name}' not registered")
        return self._custom_masks[name](value)

    def mask_dict(self, data: Dict, fields: list, mask_func: Optional[Callable] = None) -> Dict:
        result = dict(data)
        default_func = mask_func or self._mask_middle
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = default_func(result[field])
        return result
