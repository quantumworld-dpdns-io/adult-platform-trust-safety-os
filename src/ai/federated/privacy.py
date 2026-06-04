import math
import random
from typing import Dict, List, Optional, Tuple


class DifferentialPrivacy:
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5,
                 max_grad_norm: float = 1.0, noise_multiplier: float = 1.0):
        self._epsilon = epsilon
        self._delta = delta
        self._max_grad_norm = max_grad_norm
        self._noise_multiplier = noise_multiplier
        self._total_noise_added = 0.0
        self._total_queries = 0
        self._rdp_scale = 1e-5

    def add_noise(self, data: List[float], sensitivity: float = 1.0) -> List[float]:
        noisy_data = []
        for value in data:
            noise = random.gauss(0, sensitivity * self._noise_multiplier / self._epsilon)
            noisy_data.append(value + noise)
            self._total_noise_added += abs(noise)
        self._total_queries += 1
        return noisy_data

    def clip_gradients(self, gradients: List[float],
                        max_norm: Optional[float] = None) -> List[float]:
        norm = math.sqrt(sum(g * g for g in gradients))
        max_norm = max_norm or self._max_grad_norm
        if norm <= max_norm:
            return gradients
        scale = max_norm / norm
        return [g * scale for g in gradients]

    def compute_privacy_budget(self, num_samples: int, batch_size: int,
                                num_steps: int) -> Dict:
        q = batch_size / num_samples
        rdp = self._compute_rdp(q, self._noise_multiplier, num_steps)
        epsilon = self._rdp_to_epsilon(rdp, self._delta)
        return {
            "epsilon": epsilon,
            "delta": self._delta,
            "rdp": rdp,
            "num_steps": num_steps,
            "q": q,
            "noise_multiplier": self._noise_multiplier,
        }

    def _compute_rdp(self, q: float, noise_multiplier: float, steps: int) -> float:
        if noise_multiplier == 0:
            return float("inf")
        rdp = steps * self._rdp_gaussian_mechanism(q, noise_multiplier)
        return rdp

    def _rdp_gaussian_mechanism(self, q: float, noise_multiplier: float) -> float:
        if q == 0:
            return 0.0
        alpha = 1 + 1.0 / (noise_multiplier ** 2)
        rdp = (q ** 2) * alpha / (2 * noise_multiplier ** 2)
        return rdp

    def _rdp_to_epsilon(self, rdp: float, delta: float) -> float:
        if rdp == 0:
            return 0.0
        epsilon = rdp + math.log(1 / delta) / 1
        return epsilon

    def rdp_accountant(self, noise_multipliers: List[float],
                        steps_per_noise: List[int],
                        num_samples: int, batch_size: int) -> Dict:
        total_rdp = 0.0
        q = batch_size / num_samples
        for noise_mult, steps in zip(noise_multipliers, steps_per_noise):
            rdp = self._rdp_gaussian_mechanism(q, noise_mult) * steps
            total_rdp += rdp
        epsilon = self._rdp_to_epsilon(total_rdp, self._delta)
        return {
            "total_rdp": total_rdp,
            "epsilon": epsilon,
            "delta": self._delta,
        }

    def should_stop(self, current_epsilon: float,
                     max_epsilon: Optional[float] = None) -> bool:
        max_eps = max_epsilon or self._epsilon
        return current_epsilon >= max_eps

    def get_privacy_report(self) -> Dict:
        return {
            "epsilon": self._epsilon,
            "delta": self._delta,
            "max_grad_norm": self._max_grad_norm,
            "noise_multiplier": self._noise_multiplier,
            "total_noise_added": self._total_noise_added,
            "total_queries": self._total_queries,
        }

    def reset(self) -> None:
        self._total_noise_added = 0.0
        self._total_queries = 0
