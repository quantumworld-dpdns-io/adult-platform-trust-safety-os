import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode


class RequestSigner:
    def __init__(self, secret_key: str):
        self._secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

    def sign_request(self, method: str, path: str, body: Optional[str] = None,
                     headers: Optional[Dict[str, str]] = None, timestamp: Optional[float] = None) -> Dict[str, str]:
        if timestamp is None:
            timestamp = time.time()
        message = self._build_message(method, path, body, headers, timestamp)
        signature = self._generate_signature(message)
        return {
            "X-Signature": signature,
            "X-Timestamp": str(int(timestamp)),
            "X-Method": method.upper(),
        }

    def _build_message(self, method: str, path: str, body: Optional[str],
                        headers: Optional[Dict[str, str]], timestamp: float) -> str:
        parts = [
            method.upper(),
            path,
            str(int(timestamp)),
        ]
        if body:
            body_hash = hashlib.sha256(body.encode()).hexdigest()
            parts.append(body_hash)
        if headers:
            sorted_headers = sorted(headers.items())
            header_str = "&".join(f"{k.lower()}={v}" for k, v in sorted_headers)
            parts.append(hashlib.sha256(header_str.encode()).hexdigest())
        return "\n".join(parts)

    def _generate_signature(self, message: str) -> str:
        return hmac.new(self._secret_key, message.encode(), hashlib.sha256).hexdigest()

    def verify_signature(self, method: str, path: str, body: Optional[str],
                          headers: Optional[Dict[str, str]], signature: str,
                          timestamp: float, max_age: int = 300) -> bool:
        now = time.time()
        if abs(now - timestamp) > max_age:
            return False
        message = self._build_message(method, path, body, headers, timestamp)
        expected = self._generate_signature(message)
        return hmac.compare_digest(expected, signature)

    def generate_hmac(self, data: str, algorithm: str = "sha256") -> str:
        alg_map = {
            "sha256": hashlib.sha256,
            "sha384": hashlib.sha384,
            "sha512": hashlib.sha512,
        }
        hash_func = alg_map.get(algorithm, hashlib.sha256)
        return hmac.new(self._secret_key, data.encode(), hash_func).hexdigest()

    def verify_hmac(self, data: str, signature: str, algorithm: str = "sha256") -> bool:
        expected = self.generate_hmac(data, algorithm)
        return hmac.compare_digest(expected, signature)

    def sign_query_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        sorted_params = dict(sorted(params.items()))
        query_string = urlencode(sorted_params)
        timestamp = str(int(time.time()))
        message = f"{query_string}\n{timestamp}"
        signature = hmac.new(self._secret_key, message.encode(), hashlib.sha256).hexdigest()
        return {
            "signature": signature,
            "timestamp": timestamp,
        }

    def verify_query_params(self, params: Dict[str, Any], signature: str,
                             timestamp: str, max_age: int = 300) -> bool:
        now = time.time()
        try:
            ts = float(timestamp)
        except ValueError:
            return False
        if abs(now - ts) > max_age:
            return False
        sorted_params = dict(sorted(params.items()))
        query_string = urlencode(sorted_params)
        message = f"{query_string}\n{timestamp}"
        expected = hmac.new(self._secret_key, message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
