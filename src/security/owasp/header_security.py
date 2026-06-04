from typing import Dict, Optional


class SecurityHeaders:
    def __init__(self, domain: str = "example.com"):
        self._domain = domain

    def get_hsts_header(self, max_age: int = 31536000, include_subdomains: bool = True,
                        preload: bool = True) -> str:
        header = f"max-age={max_age}"
        if include_subdomains:
            header += "; includeSubDomains"
        if preload:
            header += "; preload"
        return header

    def get_csp_header(self, nonce: Optional[str] = None) -> str:
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-src 'self'",
            "object-src 'none'",
            "plugin-types 'none'",
        ]
        if nonce:
            directives[1] = f"script-src 'self' 'nonce-{nonce}'"
            directives[2] = f"style-src 'self' 'nonce-{nonce}'"
        return "; ".join(directives)

    def get_x_frame_options(self, option: str = "DENY") -> str:
        valid_options = ["DENY", "SAMEORIGIN"]
        if option.upper() not in valid_options:
            option = "DENY"
        return option.upper()

    def get_x_content_type_options(self) -> str:
        return "nosniff"

    def get_referrer_policy(self, policy: str = "strict-origin-when-cross-origin") -> str:
        valid_policies = [
            "no-referrer",
            "no-referrer-when-downgrade",
            "origin",
            "origin-when-cross-origin",
            "same-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
            "unsafe-url",
        ]
        if policy not in valid_policies:
            return "strict-origin-when-cross-origin"
        return policy

    def get_permissions_policy(self) -> str:
        policies = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()",
            "interest-cohort=()",
        ]
        return ", ".join(policies)

    def apply_all_headers(self, include_hsts: bool = True, include_csp: bool = True,
                           include_xfo: bool = True, include_xcto: bool = True,
                           include_rp: bool = True, include_pp: bool = True) -> Dict[str, str]:
        headers = {}
        if include_hsts:
            headers["Strict-Transport-Security"] = self.get_hsts_header()
        if include_csp:
            headers["Content-Security-Policy"] = self.get_csp_header()
        if include_xfo:
            headers["X-Frame-Options"] = self.get_x_frame_options()
        if include_xcto:
            headers["X-Content-Type-Options"] = self.get_x_content_type_options()
        if include_rp:
            headers["Referrer-Policy"] = self.get_referrer_policy()
        if include_pp:
            headers["Permissions-Policy"] = self.get_permissions_policy()
        headers["X-XSS-Protection"] = "1; mode=block"
        headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return headers

    def get_security_score(self, headers: Dict[str, str]) -> int:
        score = 0
        if "Strict-Transport-Security" in headers:
            score += 20
        if "Content-Security-Policy" in headers:
            score += 20
        if "X-Frame-Options" in headers:
            score += 15
        if "X-Content-Type-Options" in headers:
            score += 10
        if "Referrer-Policy" in headers:
            score += 10
        if "Permissions-Policy" in headers:
            score += 10
        if "X-XSS-Protection" in headers:
            score += 5
        if "X-Permitted-Cross-Domain-Policies" in headers:
            score += 5
        return score
