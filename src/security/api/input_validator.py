import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class InputValidator:
    EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    URL_REGEX = r"^https?://[^\s/$.?#].[^\s]*$"
    PHONE_REGEX = r"^\+?1?\d{9,15}$"
    UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    MAX_STRING_LENGTH = 10000
    MAX_JSON_DEPTH = 10
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    ALLOWED_UPLOAD_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "application/json",
    }

    def validate_email(self, email: str) -> Tuple[bool, str]:
        if not email or not isinstance(email, str):
            return False, "Email is required"
        email = email.strip().lower()
        if len(email) > 254:
            return False, "Email too long"
        if not re.match(self.EMAIL_REGEX, email):
            return False, "Invalid email format"
        parts = email.split("@")
        if len(parts) != 2:
            return False, "Invalid email format"
        local, domain = parts
        if not local or not domain:
            return False, "Invalid email format"
        if ".." in email:
            return False, "Invalid email format"
        return True, "Valid email"

    def validate_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> Tuple[bool, str]:
        if not url or not isinstance(url, str):
            return False, "URL is required"
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "Invalid URL format"
        if parsed.scheme.lower() not in allowed_schemes:
            return False, f"Scheme {parsed.scheme} not allowed"
        if not parsed.hostname:
            return False, "No hostname provided"
        if len(url) > 2048:
            return False, "URL too long"
        if ".." in url:
            return False, "Path traversal in URL"
        return True, "Valid URL"

    def validate_json(self, json_str: str, max_depth: int = 10) -> Tuple[bool, Any]:
        if not json_str or not isinstance(json_str, str):
            return False, "JSON string is required"
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        actual_depth = self._get_json_depth(data)
        if actual_depth > max_depth:
            return False, f"JSON too deeply nested: {actual_depth} levels"
        return True, data

    def _get_json_depth(self, obj: Any, current: int = 0) -> int:
        if current > self.MAX_JSON_DEPTH:
            return current
        if isinstance(obj, dict):
            if not obj:
                return current
            return max(self._get_json_depth(v, current + 1) for v in obj.values())
        if isinstance(obj, list):
            if not obj:
                return current
            return max(self._get_json_depth(item, current + 1) for item in obj)
        return current

    def validate_file_upload(self, filename: str, file_size: int,
                              content_type: str) -> Tuple[bool, str]:
        if not filename or not isinstance(filename, str):
            return False, "Filename is required"
        if file_size <= 0:
            return False, "File is empty"
        if file_size > self.MAX_UPLOAD_SIZE:
            return False, f"File too large: {file_size} bytes"
        if content_type not in self.ALLOWED_UPLOAD_TYPES:
            return False, f"File type {content_type} not allowed"
        dangerous_exts = [".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".msi"]
        for ext in dangerous_exts:
            if filename.lower().endswith(ext):
                return False, f"Dangerous file extension: {ext}"
        return True, "Valid file upload"

    def sanitize_string(self, value: str, max_length: int = 1000) -> str:
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        value = value[:max_length]
        value = value.replace("\x00", "")
        value = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
        return value

    def max_length_check(self, value: str, max_length: int = 1000) -> Tuple[bool, str]:
        if not isinstance(value, str):
            value = str(value)
        if len(value) > max_length:
            return False, f"Value exceeds max length of {max_length}"
        return True, "Within length limit"

    def validate_ip_address(self, ip: str) -> Tuple[bool, str]:
        import ipaddress
        try:
            ip_obj = ipaddress.ip_address(ip)
            return True, "Valid IP address"
        except ValueError:
            return False, "Invalid IP address"

    def validate_phone(self, phone: str) -> Tuple[bool, str]:
        if not phone or not isinstance(phone, str):
            return False, "Phone number is required"
        cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
        if not cleaned.isdigit():
            return False, "Phone number must contain only digits"
        if len(cleaned) < 9 or len(cleaned) > 15:
            return False, "Invalid phone number length"
        return True, "Valid phone number"

    def validate_uuid(self, uuid_str: str) -> Tuple[bool, str]:
        if not uuid_str or not isinstance(uuid_str, str):
            return False, "UUID is required"
        if re.match(self.UUID_REGEX, uuid_str.lower()):
            return True, "Valid UUID"
        return False, "Invalid UUID format"
