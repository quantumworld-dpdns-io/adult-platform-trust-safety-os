import json
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple


class FlowerServer:
    def __init__(self, model_class=None, num_clients: int = 0, num_rounds: int = 10):
        self._model_class = model_class
        self._num_clients = num_clients
        self._num_rounds = num_rounds
        self._current_round = 0
        self._global_model = None
        self._client_updates: List[Dict] = []
        self._history: List[Dict] = []
        self._model_path = "global_model.pkl"

    def start_round(self) -> int:
        self._current_round += 1
        self._client_updates = []
        return self._current_round

    def aggregate_updates(self, updates: List[Dict]) -> Dict:
        if not updates:
            return {"error": "No updates to aggregate"}
        aggregated = {}
        total_samples = sum(u.get("num_samples", 1) for u in updates)
        for key in updates[0].get("parameters", {}).keys():
            weighted_sum = 0
            for update in updates:
                params = update.get("parameters", {})
                weight = update.get("num_samples", 1) / total_samples
                weighted_sum += params.get(key, 0) * weight
            aggregated[key] = weighted_sum
        self._client_updates = updates
        return {
            "aggregated_parameters": aggregated,
            "num_updates": len(updates),
            "total_samples": total_samples,
        }

    def evaluate_global_model(self, test_data: Any = None) -> Dict:
        if self._global_model is None:
            return {"accuracy": 0.0, "loss": 1.0, "status": "no_model"}
        metrics = {
            "accuracy": 0.0,
            "loss": 1.0,
            "round": self._current_round,
            "num_clients": len(self._client_updates),
        }
        if test_data is not None:
            try:
                metrics["test_samples"] = len(test_data) if hasattr(test_data, "__len__") else 0
            except Exception:
                pass
        self._history.append(metrics)
        return metrics

    def get_model_parameters(self) -> Dict:
        if self._global_model is None:
            return {}
        if isinstance(self._global_model, dict):
            return self._global_model
        return {"model": self._global_model}

    def save_model(self, path: Optional[str] = None) -> str:
        save_path = path or self._model_path
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
        model_data = {
            "model": self._global_model,
            "round": self._current_round,
            "history": self._history,
            "config": {
                "num_clients": self._num_clients,
                "num_rounds": self._num_rounds,
            },
        }
        with open(save_path, "wb") as f:
            pickle.dump(model_data, f)
        return save_path

    def load_model(self, path: Optional[str] = None) -> bool:
        load_path = path or self._model_path
        if not os.path.exists(load_path):
            return False
        try:
            with open(load_path, "rb") as f:
                model_data = pickle.load(f)
            self._global_model = model_data.get("model")
            self._current_round = model_data.get("round", 0)
            self._history = model_data.get("history", [])
            return True
        except Exception:
            return False

    def set_global_model(self, model: Any) -> None:
        self._global_model = model

    def get_round_info(self) -> Dict:
        return {
            "current_round": self._current_round,
            "total_rounds": self._num_rounds,
            "clients_per_round": self._num_clients,
            "updates_received": len(self._client_updates),
            "history": self._history,
        }

    def reset(self) -> None:
        self._current_round = 0
        self._client_updates = []
        self._global_model = None
        self._history = []
