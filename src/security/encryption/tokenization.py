import hashlib
import secrets
import string
from typing import Dict, Optional


class PIITokenizer:
    def __init__(self, secret_key: Optional[str] = None):
        self._secret_key = secret_key or secrets.token_hex(32)
        self._token_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}
        self._format_map: Dict[str, str] = {}

    def _generate_token(self, value: str) -> str:
        h = hashlib.sha256(f"{self._secret_key}:{value}".encode()).hexdigest()
        token = f"tok_{h[:16]}"
        return token

    def _get_format(self, value: str) -> str:
        stripped = value.strip()
        if "@" in stripped and "." in stripped:
            return "email"
        cleaned = stripped.replace("-", "").replace(" ", "")
        if cleaned.isdigit():
            if len(cleaned) == 4:
                return "credit_card"
            if len(cleaned) == 9:
                return "ssn"
        return "unknown"

    def tokenize_email(self, email: str) -> str:
        token = self._generate_token(email)
        self._token_map[token] = email
        self._reverse_map[email] = token
        self._format_map[token] = "email"
        return token

    def tokenize_ssn(self, ssn: str) -> str:
        token = self._generate_token(ssn)
        self._token_map[token] = ssn
        self._reverse_map[ssn] = token
        self._format_map[token] = "ssn"
        return token

    def tokenize_credit_card(self, card_number: str) -> str:
        token = self._generate_token(card_number)
        self._token_map[token] = card_number
        self._reverse_map[card_number] = token
        self._format_map[token] = "credit_card"
        return token

    def detokenize(self, token: str) -> Optional[str]:
        return self._token_map.get(token)

    def get_token_format(self, token: str) -> str:
        return self._format_map.get(token, "unknown")

    def bulk_tokenize(self, values: list) -> list:
        return [self._generate_token(v) for v in values]


def tokenize_email(email: str, tokenizer: Optional[PIITokenizer] = None) -> str:
    t = tokenizer or PIITokenizer()
    return t.tokenize_email(email)


def tokenize_ssn(ssn: str, tokenizer: Optional[PIITokenizer] = None) -> str:
    t = tokenizer or PIITokenizer()
    return t.tokenize_ssn(ssn)


def tokenize_credit_card(card_number: str, tokenizer: Optional[PIITokenizer] = None) -> str:
    t = tokenizer or PIITokenizer()
    return t.tokenize_credit_card(card_number)


def detokenize(token: str, tokenizer: PIITokenizer) -> Optional[str]:
    return tokenizer.detokenize(token)


def get_token_format(token: str, tokenizer: PIITokenizer) -> str:
    return tokenizer.get_token_format(token)
