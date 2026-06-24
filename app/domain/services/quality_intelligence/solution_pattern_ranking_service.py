from __future__ import annotations

from typing import Any


class SolutionPatternRankingService:
    """Ranking de padrões por aderência a filtros declarativos."""

    def score_pattern(
        self,
        *,
        problem_category: str | None,
        failure_mode: str | None,
        root_cause_category: str | None,
        symptom_tags: list[str],
        pattern: dict[str, Any],
    ) -> float:
        score = 0.0
        if problem_category and pattern.get("problem_category"):
            if problem_category.strip().lower() == str(pattern["problem_category"]).strip().lower():
                score += 0.35

        if failure_mode and pattern.get("failure_mode"):
            fm = failure_mode.strip().lower()
            pattern_fm = str(pattern["failure_mode"]).strip().lower()
            if fm == pattern_fm or fm in pattern_fm or pattern_fm in fm:
                score += 0.30

        if root_cause_category and pattern.get("root_cause_category"):
            if (
                root_cause_category.strip().lower()
                == str(pattern["root_cause_category"]).strip().lower()
            ):
                score += 0.20

        query_tags = {t.strip().lower() for t in symptom_tags if t.strip()}
        pattern_tags = {
            t.strip().lower() for t in (pattern.get("symptom_tags") or []) if t.strip()
        }
        if query_tags and pattern_tags:
            overlap = len(query_tags & pattern_tags) / len(query_tags | pattern_tags)
            score += overlap * 0.15

        rate = pattern.get("effectiveness_rate")
        if rate is not None:
            score += float(rate) * 0.05

        usage = int(pattern.get("usage_count") or 0)
        if usage > 0:
            score += min(usage / 100, 0.05)

        return round(min(score, 1.0), 4)

    def rank_patterns(
        self,
        patterns: list[dict[str, Any]],
        *,
        problem_category: str | None,
        failure_mode: str | None,
        root_cause_category: str | None,
        symptom_tags: list[str],
        limit: int = 10,
        min_score: float = 0.1,
    ) -> list[dict[str, Any]]:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for pattern in patterns:
            score = self.score_pattern(
                problem_category=problem_category,
                failure_mode=failure_mode,
                root_cause_category=root_cause_category,
                symptom_tags=symptom_tags,
                pattern=pattern,
            )
            if score >= min_score:
                ranked.append((score, pattern))

        ranked.sort(
            key=lambda item: (
                item[0],
                float(item[1].get("effectiveness_rate") or 0),
                int(item[1].get("usage_count") or 0),
            ),
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for score, pattern in ranked[:limit]:
            results.append(
                {
                    "id": str(pattern["id"]),
                    "title": pattern["title"],
                    "effectiveness_rate": pattern.get("effectiveness_rate"),
                    "usage_count": pattern.get("usage_count"),
                    "recommended_actions": pattern.get("recommended_actions") or [],
                    "actions_to_avoid": pattern.get("actions_to_avoid") or [],
                    "relevance_score": score,
                }
            )
        return results
