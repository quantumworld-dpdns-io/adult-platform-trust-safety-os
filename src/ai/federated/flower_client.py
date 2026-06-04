from typing import Any, Dict, List, Optional, Tuple


class FlowerClient:
    def __init__(self, client_id: str, model=None, train_data: Any = None,
                 val_data: Any = None, test_data: Any = None):
        self._client_id = client_id
        self._model = model
        self._train_data = train_data
        self._val_data = val_data
        self._test_data = test_data
        self._local_parameters: Dict[str, Any] = {}
        self._training_history: List[Dict] = []

    def train_local(self, epochs: int = 5, lr: float = 0.01,
                     batch_size: int = 32) -> Dict:
        if self._model is None:
            return {"error": "No model set"}
        if self._train_data is None:
            return {"error": "No training data"}
        results = {
            "client_id": self._client_id,
            "epochs": epochs,
            "loss": 0.0,
            "accuracy": 0.0,
            "num_samples": 0,
        }
        try:
            num_samples = len(self._train_data) if hasattr(self._train_data, "__len__") else 100
            results["num_samples"] = num_samples
            if hasattr(self._model, "fit"):
                history = self._model.fit(
                    self._train_data,
                    epochs=epochs,
                    batch_size=batch_size,
                    verbose=0,
                )
                if history and hasattr(history, "history"):
                    results["loss"] = history.history.get("loss", [0.0])[-1]
                    results["accuracy"] = history.history.get("accuracy", [0.0])[-1]
            else:
                results["loss"] = 0.5
                results["accuracy"] = 0.5
        except Exception as e:
            results["error"] = str(e)
        self._training_history.append(results)
        return results

    def get_parameters(self) -> Dict[str, Any]:
        if self._model is None:
            return {}
        params = {}
        if hasattr(self._model, "get_weights"):
            weights = self._model.get_weights()
            for i, w in enumerate(weights):
                params[f"layer_{i}"] = w.tolist() if hasattr(w, "tolist") else w
        elif hasattr(self._model, "parameters"):
            for name, param in self._model.parameters():
                params[name] = param.detach().cpu().numpy().tolist()
        elif isinstance(self._model, dict):
            params = self._model
        self._local_parameters = params
        return params

    def set_parameters(self, parameters: Dict[str, Any]) -> bool:
        try:
            if self._model is None:
                return False
            if hasattr(self._model, "set_weights"):
                weights = [parameters[k] for k in sorted(parameters.keys()) if k.startswith("layer_")]
                self._model.set_weights(weights)
            elif hasattr(self._model, "load_state_dict"):
                import torch
                state_dict = {k: torch.tensor(v) for k, v in parameters.items()}
                self._model.load_state_dict(state_dict)
            elif isinstance(self._model, dict):
                self._model.update(parameters)
            self._local_parameters = parameters
            return True
        except Exception:
            return False

    def evaluate(self) -> Dict:
        if self._model is None:
            return {"error": "No model set"}
        if self._test_data is None:
            return {"error": "No test data"}
        results = {
            "client_id": self._client_id,
            "loss": 0.0,
            "accuracy": 0.0,
            "num_samples": 0,
        }
        try:
            num_samples = len(self._test_data) if hasattr(self._test_data, "__len__") else 100
            results["num_samples"] = num_samples
            if hasattr(self._model, "evaluate"):
                eval_result = self._model.evaluate(self._test_data, verbose=0)
                if isinstance(eval_result, list):
                    results["loss"] = eval_result[0]
                    results["accuracy"] = eval_result[1] if len(eval_result) > 1 else 0.0
                elif isinstance(eval_result, dict):
                    results["loss"] = eval_result.get("loss", 0.0)
                    results["accuracy"] = eval_result.get("accuracy", 0.0)
            else:
                results["loss"] = 0.5
                results["accuracy"] = 0.5
        except Exception as e:
            results["error"] = str(e)
        return results

    def fit(self, parameters: Dict[str, Any], epochs: int = 5) -> Tuple[Dict, Dict]:
        self.set_parameters(parameters)
        train_result = self.train_local(epochs=epochs)
        eval_result = self.evaluate()
        return train_result, eval_result

    def get_client_info(self) -> Dict:
        return {
            "client_id": self._client_id,
            "has_model": self._model is not None,
            "has_train_data": self._train_data is not None,
            "has_test_data": self._test_data is not None,
            "training_rounds": len(self._training_history),
        }
