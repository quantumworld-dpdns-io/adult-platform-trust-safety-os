import html
import re
from typing import List, Optional
from urllib.parse import urlparse, quote


class XSSPrevention:
    DANGEROUS_TAGS = [
        "script", "iframe", "object", "embed", "form", "input",
        "textarea", "button", "select", "link", "meta", "base",
        "applet", "style", "svg", "math",
    ]

    DANGEROUS_ATTRS = [
        "onload", "onerror", "onclick", "onmouseover", "onmouseout",
        "onfocus", "onblur", "onsubmit", "onchange", "onkeydown",
        "onkeyup", "onkeypress", "onmousedown", "onmouseup",
        "javascript:", "vbscript:", "data:",
    ]

    def escape_html(self, text: str) -> str:
        return html.escape(text, quote=True)

    def sanitize_output(self, text: str, allowed_tags: Optional[List[str]] = None) -> str:
        if allowed_tags is None:
            allowed_tags = ["p", "br", "strong", "em", "u", "ol", "ul", "li", "h1", "h2", "h3", "h4", "h5", "h6", "a", "img"]
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<object[^>]*>.*?</object>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<embed[^>]*>", "", text, flags=re.IGNORECASE)
        for attr in self.DANGEROUS_ATTRS:
            text = re.sub(rf"\s*{attr}\s*=\s*[\"'][^\"']*[\"']", "", text, flags=re.IGNORECASE)
        def replace_tag(match):
            tag = match.group(1).lower()
            if tag in allowed_tags:
                return match.group(0)
            return ""
        text = re.sub(r"<(/?)(\w+)[^>]*>", replace_tag, text)
        return text

    def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https", "mailto", "tel"]:
                return False
            if parsed.scheme in ["javascript", "vbscript", "data"]:
                return False
            if re.search(r"javascript:", url, re.IGNORECASE):
                return False
            return True
        except Exception:
            return False

    def strip_tags(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", text)

    def csp_header(self, nonce: Optional[str] = None) -> str:
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        if nonce:
            directives[1] = f"script-src 'self' 'nonce-{nonce}'"
            directives[2] = f"style-src 'self' 'nonce-{nonce}'"
        return "; ".join(directives)

    def sanitize_attribute(self, value: str) -> str:
        value = value.replace('"', "&quot;")
        value = value.replace("'", "&#x27;")
        value = value.replace("<", "&lt;")
        value = value.replace(">", "&gt;")
        return value

    def sanitize_css(self, css: str) -> str:
        css = re.sub(r"expression\s*\(", "", css, flags=re.IGNORECASE)
        css = re.sub(r"url\s*\(\s*['\"]?\s*javascript:", "", css, flags=re.IGNORECASE)
        css = re.sub(r"@import\s+[^;]+;", "", css, flags=re.IGNORECASE)
        css = re.sub(r"behavior\s*:", "", css, flags=re.IGNORECASE)
        return css

    def is_safe_uri(self, uri: str) -> bool:
        dangerous_schemes = ["javascript", "vbscript", "data", "blob"]
        parsed = urlparse(uri)
        return parsed.scheme.lower() not in dangerous_schemes
