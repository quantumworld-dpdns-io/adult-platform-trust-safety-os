import re
import html
from typing import Any, Dict, List, Optional
from urllib.parse import quote


class InjectionPrevention:
    SQL_PATTERNS = [
        r"(?i)(\b(union|select|insert|update|delete|drop|alter|create|exec|execute|truncate|declare|exec|xp_)\b)",
        r"(?i)(--|#|/\*|\*/)",
        r"(?i)(\b(or|and)\b\s+\d+\s*=\s*\d+)",
        r"(?i)('\s*(or|and)\s+')",
        r"(?i)(;.*\b(drop|alter|create)\b)",
    ]

    NOSQL_PATTERNS = [
        r"\$where",
        r"\$regex",
        r"\$ne",
        r"\$gt",
        r"\$lt",
        r"\$exists",
        r"\$nin",
        r"\$in",
    ]

    LDAP_PATTERNS = [
        r"[()=*|&!]",
        r"\x00",
    ]

    OS_COMMAND_PATTERNS = [
        r"[;&|`$]",
        r"\.\.",
        r"~",
    ]

    def sanitize_sql(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        value = value.replace("'", "''")
        value = value.replace(";", "")
        value = re.sub(r"(?i)(--|#|/\*|\*/)", "", value)
        dangerous_keywords = [
            "UNION", "SELECT", "INSERT", "UPDATE", "DELETE", "DROP",
            "ALTER", "CREATE", "EXEC", "EXECUTE", "TRUNCATE", "DECLARE",
        ]
        for keyword in dangerous_keywords:
            pattern = rf"(?i)\b{keyword}\b"
            if re.search(pattern, value):
                raise ValueError(f"Potentially dangerous SQL keyword detected: {keyword}")
        return value

    def sanitize_nosql(self, value: Any) -> Any:
        if isinstance(value, str):
            for pattern in self.NOSQL_PATTERNS:
                if re.search(pattern, value):
                    raise ValueError(f"Potentially dangerous NoSQL operator detected in: {value}")
            return html.escape(value)
        if isinstance(value, dict):
            sanitized = {}
            for key, val in value.items():
                if key.startswith("$"):
                    raise ValueError(f"Potentially dangerous NoSQL operator: {key}")
                sanitized[key] = self.sanitize_nosql(val)
            return sanitized
        if isinstance(value, list):
            return [self.sanitize_nosql(item) for item in value]
        return value

    def sanitize_ldap(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        special_chars = {
            "*": r"\2a",
            "(": r"\28",
            ")": r"\29",
            "\\": r"\5c",
            "\x00": r"\00",
        }
        for char, replacement in special_chars.items():
            value = value.replace(char, replacement)
        return value

    def sanitize_os_command(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if re.search(r"[;&|`$]", value):
            raise ValueError(f"Potentially dangerous character in OS command: {value}")
        if ".." in value:
            raise ValueError("Path traversal detected in OS command")
        return value

    def validate_input(self, value: str, input_type: str = "general") -> str:
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        value = value.replace("\x00", "")
        if len(value) > 10000:
            raise ValueError("Input too long")
        return value

    def sanitize_for_context(self, value: str, context: str) -> str:
        if context == "sql":
            return self.sanitize_sql(value)
        elif context == "nosql":
            return self.sanitize_nosql(value)
        elif context == "ldap":
            return self.sanitize_ldap(value)
        elif context == "os":
            return self.sanitize_os_command(value)
        elif context == "html":
            return html.escape(value)
        elif context == "url":
            return quote(value)
        return self.validate_input(value)
