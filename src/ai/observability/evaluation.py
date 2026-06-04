from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    metric: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)
    passed: bool = False


@dataclass
class BenchmarkResult:
    name: str
    total: int
    passed: int
    failed: int
    avg_score: float
    results: list[EvaluationResult] = field(default_factory=list)


class LLMEvaluator:
    def __init__(self, ollama_client=None) -> None:
        self._ollama = ollama_client
        self._evaluation_history: list[dict[str, Any]] = []

    async def evaluate_accuracy(
        self,
        question: str,
        answer: str,
        expected_answer: str,
        context: str | None = None,
    ) -> EvaluationResult:
        score = 0.0
        details: dict[str, Any] = {}

        answer_lower = answer.lower().strip()
        expected_lower = expected_answer.lower().strip()

        if answer_lower == expected_lower:
            score = 1.0
        elif expected_lower in answer_lower or answer_lower in expected_lower:
            score = 0.8
        else:
            answer_words = set(answer_lower.split())
            expected_words = set(expected_lower.split())
            if expected_words:
                overlap = answer_words & expected_words
                score = len(overlap) / len(expected_words)
                score = min(score, 1.0)

        details["exact_match"] = answer_lower == expected_lower
        details["word_overlap"] = score

        if self._ollama is not None and score < 0.5:
            try:
                judge_prompt = (
                    f"Rate the similarity between these answers on a scale of 0 to 1:\n"
                    f"Question: {question}\n"
                    f"Expected: {expected_answer}\n"
                    f"Got: {answer}\n"
                    f"Respond with only a number between 0 and 1."
                )
                result = await self._ollama.generate(
                    model="llama3.1",
                    prompt=judge_prompt,
                    temperature=0.0,
                    max_tokens=10,
                )
                if isinstance(result, dict):
                    response_text = result.get("response", "")
                    nums = re.findall(r"0?\.\d+|1\.0", response_text)
                    if nums:
                        llm_score = float(nums[0])
                        score = (score + llm_score) / 2
                        details["llm_judged_score"] = llm_score
            except Exception as exc:
                logger.warning("LLM accuracy judgment failed: %s", exc)

        self._record_evaluation("accuracy", score, details)
        return EvaluationResult(metric="accuracy", score=score, details=details, passed=score >= 0.7)

    async def evaluate_relevance(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> EvaluationResult:
        score = 0.0
        details: dict[str, Any] = {}

        question_words = set(question.lower().split())
        context_words = set(context.lower().split())
        answer_words = set(answer.lower().split())

        q_in_answer = len(question_words & answer_words) / max(len(question_words), 1)
        c_in_answer = len(context_words & answer_words) / max(len(context_words), 1)

        score = q_in_answer * 0.5 + c_in_answer * 0.5
        score = min(score, 1.0)

        details["question_coverage"] = q_in_answer
        details["context_coverage"] = c_in_answer

        if self._ollama is not None:
            try:
                judge_prompt = (
                    f"Rate how relevant this answer is to the question, using context.\n"
                    f"Scale 0-1.\n"
                    f"Question: {question}\n"
                    f"Context: {context[:500]}\n"
                    f"Answer: {answer[:500]}\n"
                    f"Respond with only a number."
                )
                result = await self._ollama.generate(
                    model="llama3.1",
                    prompt=judge_prompt,
                    temperature=0.0,
                    max_tokens=10,
                )
                if isinstance(result, dict):
                    nums = re.findall(r"0?\.\d+|1\.0", result.get("response", ""))
                    if nums:
                        llm_score = float(nums[0])
                        score = (score + llm_score) / 2
                        details["llm_relevance_score"] = llm_score
            except Exception as exc:
                logger.warning("LLM relevance judgment failed: %s", exc)

        self._record_evaluation("relevance", score, details)
        return EvaluationResult(metric="relevance", score=score, details=details, passed=score >= 0.6)

    async def evaluate_hallucination(
        self,
        answer: str,
        context: str,
        source_documents: list[str] | None = None,
    ) -> EvaluationResult:
        score = 0.0
        details: dict[str, Any] = {}

        answer_sentences = [s.strip() for s in re.split(r"[.!?]", answer) if s.strip()]
        context_lower = context.lower()

        supported = 0
        unsupported = 0
        for sentence in answer_sentences:
            words = set(sentence.lower().split())
            if words and (words & set(context_lower.split())):
                supported += 1
            else:
                unsupported += 1

        total = supported + unsupported
        if total > 0:
            score = supported / total
            details["supported_sentences"] = supported
            details["unsupported_sentences"] = unsupported

        if self._ollama is not None:
            try:
                judge_prompt = (
                    "Identify which sentences in the answer are NOT supported by the context.\n"
                    f"Context:\n{context[:1000]}\n\n"
                    f"Answer:\n{answer[:1000]}\n\n"
                    "List unsupported sentences or say 'none'."
                )
                result = await self._ollama.generate(
                    model="llama3.1",
                    prompt=judge_prompt,
                    temperature=0.0,
                    max_tokens=200,
                )
                if isinstance(result, dict):
                    response_text = result.get("response", "")
                    if "none" in response_text.lower():
                        llm_score = 1.0
                    else:
                        unsupported_count = response_text.lower().count("unsupported") + response_text.count("-")
                        llm_score = max(0, 1.0 - unsupported_count * 0.15)
                    score = (score + llm_score) / 2
                    details["llm_hallucination_score"] = llm_score
            except Exception as exc:
                logger.warning("LLM hallucination check failed: %s", exc)

        self._record_evaluation("hallucination", score, details)
        return EvaluationResult(metric="hallucination", score=score, details=details, passed=score >= 0.7)

    async def run_benchmark(
        self,
        test_cases: list[dict[str, Any]],
    ) -> BenchmarkResult:
        results = []
        for case in test_cases:
            question = case.get("question", "")
            answer = case.get("answer", "")
            expected = case.get("expected", "")
            context = case.get("context", "")

            accuracy = await self.evaluate_accuracy(question, answer, expected, context)
            results.append(accuracy)

            if context:
                relevance = await self.evaluate_relevance(question, answer, context)
                results.append(relevance)

                hallucination = await self.evaluate_hallucination(answer, context)
                results.append(hallucination)

        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / max(len(results), 1)

        return BenchmarkResult(
            name="default_benchmark",
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            avg_score=avg_score,
            results=results,
        )

    def _record_evaluation(self, metric: str, score: float, details: dict[str, Any]) -> None:
        self._evaluation_history.append({
            "metric": metric,
            "score": score,
            "details": details,
        })
        if len(self._evaluation_history) > 10000:
            self._evaluation_history = self._evaluation_history[-10000:]

    def get_evaluation_history(self, metric: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        history = self._evaluation_history
        if metric:
            history = [e for e in history if e["metric"] == metric]
        return history[-limit:]

    def get_average_scores(self) -> dict[str, float]:
        if not self._evaluation_history:
            return {}
        scores: dict[str, list[float]] = {}
        for entry in self._evaluation_history:
            scores.setdefault(entry["metric"], []).append(entry["score"])
        return {metric: sum(vals) / len(vals) for metric, vals in scores.items()}
