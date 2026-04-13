"""Aggregate rule + Claude dimensions into a weighted A–F grade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hireloop.core.evaluation.rule_scorer import SKIPPED, DimensionResult

_WEIGHTS: dict[str, float] = {
    "skills_match": 0.15,
    "experience_fit": 0.10,
    "location_fit": 0.05,
    "salary_fit": 0.05,
    "domain_relevance": 0.15,
    "role_match": 0.15,
    "trajectory_fit": 0.10,
    "culture_signal": 0.08,
    "red_flags": 0.10,
    "growth_potential": 0.07,
}


@dataclass
class EvaluationResult:
    overall_grade: str
    match_score: float
    recommendation: Literal["strong_match", "worth_exploring", "skip"]
    dimension_scores: dict[str, dict[str, Any]]
    reasoning: str
    red_flags: list[str] = field(default_factory=list)
    personalization: str | None = None


class Grader:
    def aggregate(
        self,
        *,
        rule_dims: dict[str, Any],
        claude_dims: dict[str, dict[str, Any]],
        overall_reasoning: str,
        red_flag_items: list[str],
        personalization_notes: str | None,
    ) -> EvaluationResult:
        weights = dict(_WEIGHTS)

        if rule_dims.get("salary_fit") is SKIPPED:
            skipped_weight = weights.pop("salary_fit")
            remainder_sum = sum(weights.values())
            for k in weights:
                weights[k] += skipped_weight * weights[k] / remainder_sum

        score = 0.0
        flat_dims: dict[str, dict[str, Any]] = {}

        for key, weight in weights.items():
            if key in rule_dims:
                dim_result: DimensionResult = rule_dims[key]
                score += weight * dim_result.score
                flat_dims[key] = {
                    "score": dim_result.score,
                    "grade": self._map_to_letter(dim_result.score),
                    "reasoning": dim_result.details,
                    "signals": dim_result.signals,
                }
            elif key in claude_dims:
                raw = claude_dims[key]
                score += weight * float(raw["score"])
                flat_dims[key] = {
                    "score": float(raw["score"]),
                    "grade": raw.get("grade", self._map_to_letter(float(raw["score"]))),
                    "reasoning": raw.get("reasoning", ""),
                    "signals": raw.get("signals", []),
                }

        grade = self._map_to_letter(score)
        return EvaluationResult(
            overall_grade=grade,
            match_score=round(score, 3),
            recommendation=self._recommendation(grade),
            dimension_scores=flat_dims,
            reasoning=overall_reasoning,
            red_flags=list(red_flag_items),
            personalization=personalization_notes,
        )

    @staticmethod
    def _map_to_letter(score: float) -> str:
        if score >= 0.92:
            return "A"
        if score >= 0.85:
            return "A-"
        if score >= 0.78:
            return "B+"
        if score >= 0.70:
            return "B"
        if score >= 0.60:
            return "B-"
        if score >= 0.50:
            return "C+"
        if score >= 0.40:
            return "C"
        if score >= 0.30:
            return "D"
        return "F"

    @staticmethod
    def _recommendation(grade: str) -> Literal["strong_match", "worth_exploring", "skip"]:
        if grade in ("A", "A-"):
            return "strong_match"
        if grade.startswith("B"):
            return "worth_exploring"
        return "skip"
