import os
import re
from typing import Optional


class PathTraversalPrevention:
    DANGEROUS_PATTERNS = [
        r"\.\.",
        r"~",
        r"\$\{",
        r"%2e%2e",
        r"%252e%252e",
        r"\.\.%2f",
        r"\.\.%5c",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
    ]

    def validate_path(self, path: str, base_dir: str = "/") -> bool:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return False
        normalized = os.path.normpath(path)
        if os.path.isabs(normalized):
            base_norm = os.path.normpath(base_dir)
            if not normalized.startswith(base_norm):
                return False
        return True

    def sanitize_filename(self, filename: str) -> str:
        filename = os.path.basename(filename)
        filename = re.sub(r"[^\w\s\-.]", "", filename)
        filename = re.sub(r"\.{2,}", ".", filename)
        filename = filename.strip(". ")
        if not filename:
            filename = "unnamed"
        return filename

    def check_directory_escape(self, path: str, base_dir: str) -> bool:
        try:
            abs_base = os.path.abspath(base_dir)
            abs_path = os.path.abspath(os.path.join(base_dir, path))
            return abs_path.startswith(abs_base)
        except (ValueError, OSError):
            return False

    def safe_join_path(self, base_dir: str, *paths: str) -> Optional[str]:
        try:
            joined = os.path.join(base_dir, *paths)
            normalized = os.path.normpath(joined)
            abs_base = os.path.abspath(base_dir)
            abs_joined = os.path.abspath(normalized)
            if not abs_joined.startswith(abs_base):
                return None
            return abs_joined
        except (ValueError, OSError):
            return None

    def sanitize_path(self, path: str) -> str:
        path = path.replace("\\", "/")
        path = re.sub(r"/+", "/", path)
        parts = path.split("/")
        safe_parts = []
        for part in parts:
            if part in [".", "..", ""]:
                continue
            safe_parts.append(part)
        return "/".join(safe_parts)

    def is_safe_upload_path(self, filename: str, upload_dir: str) -> bool:
        safe_name = self.sanitize_filename(filename)
        if safe_name != filename:
            return False
        return self.check_directory_escape(safe_name, upload_dir)

    def normalize_and_validate(self, path: str, allowed_dirs: list) -> bool:
        normalized = os.path.normpath(path)
        for allowed_dir in allowed_dirs:
            abs_allowed = os.path.abspath(allowed_dir)
            abs_path = os.path.abspath(os.path.join(abs_allowed, normalized))
            if abs_path.startswith(abs_allowed):
                return True
        return False

    def strip_null_bytes(self, path: str) -> str:
        return path.replace("\x00", "")
