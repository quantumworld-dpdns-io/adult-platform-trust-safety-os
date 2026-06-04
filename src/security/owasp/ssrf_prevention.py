import ipaddress
import re
from typing import List, Optional, Set
from urllib.parse import urlparse


class SSRFPrevention:
    BLOCKED_IP_RANGES = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]

    METADATA_ENDPOINTS = [
        "169.254.169.254",
        "metadata.google.internal",
        "169.254.169.254/latest/meta-data",
        "instance-data/latest/meta-data",
    ]

    ALLOWED_SCHEMES = {"http", "https"}

    def __init__(self):
        self._whitelist: Set[str] = set()
        self._blacklist: Set[str] = set()

    def validate_url(self, url: str) -> tuple[bool, str]:
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "Invalid URL format"
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            return False, f"Scheme {parsed.scheme} not allowed"
        if not parsed.hostname:
            return False, "No hostname provided"
        if parsed.hostname in self.METADATA_ENDPOINTS:
            return False, "Metadata endpoint blocked"
        for endpoint in self.METADATA_ENDPOINTS:
            if endpoint in parsed.hostname:
                return False, "Metadata endpoint pattern detected"
        return True, "URL is valid"

    def check_internal_ip(self, hostname: str) -> bool:
        import socket
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            for network in self.BLOCKED_IP_RANGES:
                if ip_obj in network:
                    return True
            return False
        except socket.gaierror:
            return False

    def block_metadata_endpoints(self, url: str) -> tuple[bool, str]:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        for endpoint in self.METADATA_ENDPOINTS:
            if endpoint in hostname or endpoint in url:
                return False, f"Metadata endpoint blocked: {endpoint}"
        if hostname.startswith("169.254."):
            return False, "Link-local address blocked"
        if re.search(r"0x[0-9a-fA-F]+", hostname):
            return False, "Hex-encoded IP detected"
        if re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", hostname):
            try:
                ip = ipaddress.ip_address(hostname.split("/")[0])
                for network in self.BLOCKED_IP_RANGES:
                    if ip in network:
                        return False, "Internal IP address detected"
            except ValueError:
                pass
        return True, "No metadata endpoint detected"

    def whitelist_domains(self, domains: List[str]) -> None:
        self._whitelist.update(domains)

    def add_to_blacklist(self, domains: List[str]) -> None:
        self._blacklist.update(domains)

    def is_domain_allowed(self, hostname: str) -> bool:
        if self._blacklist and hostname in self._blacklist:
            return False
        if self._whitelist:
            return hostname in self._whitelist
        return True

    def full_check(self, url: str) -> tuple[bool, str]:
        is_valid, msg = self.validate_url(url)
        if not is_valid:
            return False, msg
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not self.is_domain_allowed(hostname):
            return False, f"Domain {hostname} not allowed"
        is_metadata, meta_msg = self.block_metadata_endpoints(url)
        if not is_metadata:
            return False, meta_msg
        if self.check_internal_ip(hostname):
            return False, "Target is an internal IP address"
        return True, "URL passed all SSRF checks"

    def safe_request_url(self, url: str) -> Optional[str]:
        is_safe, _ = self.full_check(url)
        if is_safe:
            return url
        return None
