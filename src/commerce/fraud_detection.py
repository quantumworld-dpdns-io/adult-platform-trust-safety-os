import hashlib
import time
from typing import Dict, List, Optional


class FraudDetector:
    def __init__(self):
        self._transaction_history: Dict[str, List[Dict]] = {}
        self._blocked_users: set = set()
        self._velocity_limits = {
            "per_minute": 5,
            "per_hour": 20,
            "per_day": 100,
        }
        self._risk_thresholds = {
            "low": 30,
            "medium": 60,
            "high": 80,
            "critical": 95,
        }

    def analyze_transaction(self, transaction: Dict) -> Dict:
        risk_score = 0
        risk_factors = []
        amount = transaction.get("amount", 0)
        if amount > 1000:
            risk_score += 20
            risk_factors.append("high_amount")
        if amount > 10000:
            risk_score += 30
            risk_factors.append("very_high_amount")
        user_id = transaction.get("user_id")
        if user_id and user_id in self._blocked_users:
            risk_score = 100
            risk_factors.append("blocked_user")
            return {
                "risk_score": risk_score,
                "risk_level": "critical",
                "risk_factors": risk_factors,
                "recommended_action": "block",
                "transaction_id": transaction.get("id"),
            }
        velocity_result = self.check_velocity(user_id, transaction.get("timestamp", time.time()))
        if velocity_result.get("exceeded"):
            risk_score += 30
            risk_factors.append("velocity_exceeded")
        anomaly_result = self.detect_anomaly(transaction)
        if anomaly_result.get("is_anomaly"):
            risk_score += 25
            risk_factors.append("anomaly_detected")
        risk_score = min(risk_score, 100)
        risk_level = self._get_risk_level(risk_score)
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommended_action": self._get_recommended_action(risk_level),
            "transaction_id": transaction.get("id"),
        }

    def check_velocity(self, user_id: str, current_time: float) -> Dict:
        if not user_id:
            return {"exceeded": False}
        if user_id not in self._transaction_history:
            self._transaction_history[user_id] = []
        self._transaction_history[user_id].append(current_time)
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        recent_txns = self._transaction_history[user_id]
        per_minute = len([t for t in recent_txns if t > minute_ago])
        per_hour = len([t for t in recent_txns if t > hour_ago])
        per_day = len([t for t in recent_txns if t > day_ago])
        exceeded = (
            per_minute > self._velocity_limits["per_minute"] or
            per_hour > self._velocity_limits["per_hour"] or
            per_day > self._velocity_limits["per_day"]
        )
        return {
            "exceeded": exceeded,
            "per_minute": per_minute,
            "per_hour": per_hour,
            "per_day": per_day,
        }

    def detect_anomaly(self, transaction: Dict) -> Dict:
        amount = transaction.get("amount", 0)
        is_anomaly = False
        reasons = []
        if amount > 5000:
            is_anomaly = True
            reasons.append("unusually_high_amount")
        user_id = transaction.get("user_id")
        if user_id and user_id in self._transaction_history:
            history = self._transaction_history[user_id]
            if len(history) > 5:
                avg_amount = sum(t.get("amount", 0) for t in history[-10:]) / min(len(history), 10)
                if amount > avg_amount * 5:
                    is_anomaly = True
                    reasons.append("deviation_from_average")
        return {
            "is_anomaly": is_anomaly,
            "reasons": reasons,
        }

    def get_risk_score(self, transaction: Dict) -> int:
        result = self.analyze_transaction(transaction)
        return result["risk_score"]

    def block_suspicious(self, user_id: str, reason: str = "fraud_detected") -> bool:
        self._blocked_users.add(user_id)
        return True

    def unblock_user(self, user_id: str) -> bool:
        if user_id in self._blocked_users:
            self._blocked_users.remove(user_id)
            return True
        return False

    def _get_risk_level(self, score: int) -> str:
        if score >= self._risk_thresholds["critical"]:
            return "critical"
        elif score >= self._risk_thresholds["high"]:
            return "high"
        elif score >= self._risk_thresholds["medium"]:
            return "medium"
        elif score >= self._risk_thresholds["low"]:
            return "low"
        return "minimal"

    def _get_recommended_action(self, risk_level: str) -> str:
        actions = {
            "minimal": "approve",
            "low": "approve",
            "medium": "review",
            "high": "review",
            "critical": "block",
        }
        return actions.get(risk_level, "review")

    def get_transaction_summary(self, user_id: str) -> Dict:
        if user_id not in self._transaction_history:
            return {"total_transactions": 0, "user_id": user_id}
        history = self._transaction_history[user_id]
        return {
            "user_id": user_id,
            "total_transactions": len(history),
            "is_blocked": user_id in self._blocked_users,
        }
