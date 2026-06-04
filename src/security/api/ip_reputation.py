import ipaddress
import time
from typing import Dict, List, Optional, Set


class IPReputationChecker:
    def __init__(self):
        self._blocklist: Set[str] = set()
        self._allowlist: Set[str] = set()
        self._suspicious: Dict[str, Dict] = {}
        self._threat_intel: Dict[str, Dict] = {}
        self._rate_limits: Dict[str, list] = {}

    def check_ip(self, ip: str) -> Dict:
        result = {
            "ip": ip,
            "is_blocked": ip in self._blocklist,
            "is_allowed": ip in self._allowlist,
            "is_suspicious": ip in self._suspicious,
            "threat_score": self._calculate_threat_score(ip),
            "categories": self._get_threat_categories(ip),
            "recommendation": "allow",
        }
        if result["is_blocked"]:
            result["recommendation"] = "block"
        elif result["threat_score"] > 70:
            result["recommendation"] = "monitor"
        elif result["threat_score"] > 90:
            result["recommendation"] = "block"
        return result

    def _calculate_threat_score(self, ip: str) -> int:
        score = 0
        if ip in self._blocklist:
            score += 50
        if ip in self._suspicious:
            score += self._suspicious[ip].get("score", 30)
        if ip in self._threat_intel:
            score += self._threat_intel[ip].get("threat_score", 20)
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                score += 10
            if ip_obj.is_loopback:
                score += 20
        except ValueError:
            score += 30
        return min(score, 100)

    def _get_threat_categories(self, ip: str) -> List[str]:
        categories = []
        if ip in self._threat_intel:
            categories.extend(self._threat_intel[ip].get("categories", []))
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                categories.append("private")
            if ip_obj.is_loopback:
                categories.append("loopback")
        except ValueError:
            categories.append("invalid")
        return categories

    def block_ip(self, ip: str, reason: str = "manual") -> bool:
        self._blocklist.add(ip)
        self._suspicious[ip] = {
            "reason": reason,
            "blocked_at": time.time(),
            "score": 100,
        }
        return True

    def unblock_ip(self, ip: str) -> bool:
        if ip in self._blocklist:
            self._blocklist.remove(ip)
            if ip in self._suspicious:
                del self._suspicious[ip]
            return True
        return False

    def get_blocklist(self) -> List[str]:
        return list(self._blocklist)

    def is_known_bad_ip(self, ip: str) -> bool:
        if ip in self._blocklist:
            return True
        if ip in self._threat_intel:
            return self._threat_intel[ip].get("threat_score", 0) > 80
        return False

    def add_to_threat_intel(self, ip: str, threat_score: int, categories: List[str]) -> None:
        self._threat_intel[ip] = {
            "threat_score": threat_score,
            "categories": categories,
            "updated_at": time.time(),
        }

    def mark_suspicious(self, ip: str, reason: str, score: int = 50) -> None:
        self._suspicious[ip] = {
            "reason": reason,
            "score": score,
            "detected_at": time.time(),
        }

    def get_suspicious_ips(self) -> Dict[str, Dict]:
        return dict(self._suspicious)

    def clear_all(self) -> None:
        self._blocklist.clear()
        self._allowlist.clear()
        self._suspicious.clear()
        self._threat_intel.clear()
        self._rate_limits.clear()
