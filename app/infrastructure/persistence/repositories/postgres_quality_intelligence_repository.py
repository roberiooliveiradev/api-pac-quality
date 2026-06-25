from __future__ import annotations

from typing import Any

from app.domain.services.quality_intelligence.case_similarity_embedding_service import (
    CaseSimilarityEmbeddingService,
)
from app.domain.ports.quality_action_plan_repository_port import serialize_row
from app.infrastructure.persistence.plugins.plugin_base_repository import (
    PluginBaseRepository,
    PluginsRepositoryError,
)


class PostgresQualityIntelligenceRepository(PluginBaseRepository):
    def sync_case_similarity_index(self, plan_id: str) -> str | None:
        row = self.fetch_one(
            """
            SELECT p.id,
                   p.title,
                   p.reported_problem,
                   p.product_code,
                   p.customer_name,
                   p.problem_category,
                   p.failure_mode,
                   p.root_cause_category,
                   p.symptom_tags,
                   p.branch_code,
                   p.product_description,
                   fw.root_cause
              FROM quality.quality_action_plans p
              LEFT JOIN quality.quality_five_whys fw ON fw.plan_id = p.id
             WHERE p.id = %s
               AND p.deleted_at IS NULL
            """,
            (plan_id,),
        )
        if not row:
            return None

        parts = [
            row.get("title"),
            row.get("reported_problem"),
            row.get("failure_mode"),
            row.get("problem_category"),
            row.get("product_description"),
            row.get("root_cause"),
        ]
        search_text = " ".join(part.strip() for part in parts if part and str(part).strip())

        self.execute(
            """
            INSERT INTO quality.quality_case_similarity_index (
                plan_id,
                search_text,
                product_code,
                customer_name,
                problem_category,
                failure_mode,
                root_cause_category,
                symptom_tags,
                branch_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (plan_id) DO UPDATE SET
                search_text = EXCLUDED.search_text,
                product_code = EXCLUDED.product_code,
                customer_name = EXCLUDED.customer_name,
                problem_category = EXCLUDED.problem_category,
                failure_mode = EXCLUDED.failure_mode,
                root_cause_category = EXCLUDED.root_cause_category,
                symptom_tags = EXCLUDED.symptom_tags,
                branch_code = EXCLUDED.branch_code,
                updated_at = NOW()
            """,
            (
                plan_id,
                search_text,
                row.get("product_code"),
                row.get("customer_name"),
                row.get("problem_category"),
                row.get("failure_mode"),
                row.get("root_cause_category") or row.get("root_cause"),
                row.get("symptom_tags") or [],
                row.get("branch_code"),
            ),
        )
        return search_text

    def update_search_embedding(self, plan_id: str, embedding: list[float]) -> None:
        literal = CaseSimilarityEmbeddingService.format_pgvector_literal(embedding)
        self.execute(
            """
            UPDATE quality.quality_case_similarity_index
               SET search_embedding = %s::vector,
                   updated_at = NOW()
             WHERE plan_id = %s
            """,
            (literal, plan_id),
        )

    def fetch_similar_case_candidates(
        self,
        *,
        problem_description: str,
        product_code: str | None,
        symptoms: list[str],
        branch_code: str | None = None,
        query_embedding: list[float] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        text_rows = self._fetch_text_similar_case_candidates(
            problem_description=problem_description,
            product_code=product_code,
            symptoms=symptoms,
            branch_code=branch_code,
            limit=limit,
        )

        if not query_embedding:
            return text_rows

        semantic_rows = self._fetch_semantic_similar_case_candidates(
            query_embedding=query_embedding,
            product_code=product_code,
            symptoms=symptoms,
            branch_code=branch_code,
            limit=limit,
        )
        return self._merge_similar_case_candidates(text_rows, semantic_rows)

    def _fetch_text_similar_case_candidates(
        self,
        *,
        problem_description: str,
        product_code: str | None,
        symptoms: list[str],
        branch_code: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        tokens = [t.strip() for t in problem_description.split() if len(t.strip()) >= 3][:8]
        filters = ["p.deleted_at IS NULL", "p.status NOT IN ('draft', 'cancelled')"]
        params: list[Any] = []

        or_parts: list[str] = []
        if product_code:
            or_parts.append("idx.product_code = %s")
            params.append(product_code)

        if branch_code:
            filters.append("p.branch_code = %s")
            params.append(branch_code)

        if symptoms:
            or_parts.append("idx.symptom_tags && %s::text[]")
            params.append(symptoms)

        for token in tokens[:5]:
            or_parts.append("idx.search_text ILIKE %s")
            params.append(f"%{token}%")

        if or_parts:
            filters.append(f"({' OR '.join(or_parts)})")

        where_clause = " AND ".join(filters)
        rows = self.fetch_all(
            f"""
            SELECT idx.plan_id,
                   p.code AS plan_code,
                   idx.search_text,
                   idx.product_code,
                   idx.failure_mode,
                   idx.root_cause_category,
                   idx.symptom_tags,
                   p.branch_code,
                   COALESCE(p.reported_problem, p.title) AS problem_summary,
                   fw.root_cause,
                   p.effectiveness_status,
                   p.closed_at,
                   p.title
              FROM quality.quality_case_similarity_index idx
              JOIN quality.quality_action_plans p ON p.id = idx.plan_id
              LEFT JOIN quality.quality_five_whys fw ON fw.plan_id = p.id
             WHERE {where_clause}
             ORDER BY p.updated_at DESC
             LIMIT %s
            """,
            tuple([*params, limit]),
        )

        results: list[dict[str, Any]] = []
        for row in rows:
            plan_id = str(row["plan_id"])
            actions = self.fetch_all(
                """
                SELECT description
                  FROM quality.quality_actions
                 WHERE plan_id = %s
                   AND status = 'completed'
                 ORDER BY completed_at DESC NULLS LAST
                 LIMIT 5
                """,
                (plan_id,),
            )
            effective_actions = [a["description"] for a in actions if a.get("description")]
            closed_at = row.get("closed_at")
            results.append(
                {
                    "plan_id": plan_id,
                    "plan_code": row["plan_code"],
                    "search_text": row.get("search_text") or "",
                    "product_code": row.get("product_code"),
                    "failure_mode": row.get("failure_mode"),
                    "root_cause_category": row.get("root_cause_category"),
                    "symptom_tags": list(row.get("symptom_tags") or []),
                    "problem_summary": row.get("problem_summary") or row.get("title"),
                    "root_cause": row.get("root_cause"),
                    "effectiveness_status": row.get("effectiveness_status"),
                    "closed_at": closed_at.isoformat() if hasattr(closed_at, "isoformat") else closed_at,
                    "effective_actions": effective_actions,
                    "branch_code": row.get("branch_code"),
                    "semantic_similarity": None,
                }
            )
        return results

    def _fetch_semantic_similar_case_candidates(
        self,
        *,
        query_embedding: list[float],
        product_code: str | None,
        symptoms: list[str],
        branch_code: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        literal = CaseSimilarityEmbeddingService.format_pgvector_literal(query_embedding)
        filters = [
            "p.deleted_at IS NULL",
            "p.status NOT IN ('draft', 'cancelled')",
            "idx.search_embedding IS NOT NULL",
        ]
        params: list[Any] = [literal, literal]

        if product_code:
            filters.append("idx.product_code = %s")
            params.append(product_code)

        if branch_code:
            filters.append("p.branch_code = %s")
            params.append(branch_code)

        if symptoms:
            filters.append("idx.symptom_tags && %s::text[]")
            params.append(symptoms)

        where_clause = " AND ".join(filters)
        rows = self.fetch_all(
            f"""
            SELECT idx.plan_id,
                   p.code AS plan_code,
                   idx.search_text,
                   idx.product_code,
                   idx.failure_mode,
                   idx.root_cause_category,
                   idx.symptom_tags,
                   p.branch_code,
                   COALESCE(p.reported_problem, p.title) AS problem_summary,
                   fw.root_cause,
                   p.effectiveness_status,
                   p.closed_at,
                   p.title,
                   1 - (idx.search_embedding <=> %s::vector) AS semantic_similarity
              FROM quality.quality_case_similarity_index idx
              JOIN quality.quality_action_plans p ON p.id = idx.plan_id
              LEFT JOIN quality.quality_five_whys fw ON fw.plan_id = p.id
             WHERE {where_clause}
             ORDER BY idx.search_embedding <=> %s::vector
             LIMIT %s
            """,
            tuple([*params, limit]),
        )
        return self._hydrate_similar_case_rows(rows)

    def _hydrate_similar_case_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for row in rows:
            plan_id = str(row["plan_id"])
            actions = self.fetch_all(
                """
                SELECT description
                  FROM quality.quality_actions
                 WHERE plan_id = %s
                   AND status = 'completed'
                 ORDER BY completed_at DESC NULLS LAST
                 LIMIT 5
                """,
                (plan_id,),
            )
            effective_actions = [a["description"] for a in actions if a.get("description")]
            closed_at = row.get("closed_at")
            semantic_similarity = row.get("semantic_similarity")
            results.append(
                {
                    "plan_id": plan_id,
                    "plan_code": row["plan_code"],
                    "search_text": row.get("search_text") or "",
                    "product_code": row.get("product_code"),
                    "failure_mode": row.get("failure_mode"),
                    "root_cause_category": row.get("root_cause_category"),
                    "symptom_tags": list(row.get("symptom_tags") or []),
                    "problem_summary": row.get("problem_summary") or row.get("title"),
                    "root_cause": row.get("root_cause"),
                    "effectiveness_status": row.get("effectiveness_status"),
                    "closed_at": closed_at.isoformat() if hasattr(closed_at, "isoformat") else closed_at,
                    "effective_actions": effective_actions,
                    "branch_code": row.get("branch_code"),
                    "semantic_similarity": float(semantic_similarity)
                    if semantic_similarity is not None
                    else None,
                }
            )
        return results

    @staticmethod
    def _merge_similar_case_candidates(
        text_rows: list[dict[str, Any]],
        semantic_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {
            str(row["plan_id"]): dict(row) for row in text_rows
        }

        for row in semantic_rows:
            plan_id = str(row["plan_id"])
            existing = merged.get(plan_id)
            if existing:
                existing["semantic_similarity"] = row.get("semantic_similarity")
                continue
            merged[plan_id] = dict(row)

        return list(merged.values())

    def fetch_recurrence_opening_stats(
        self,
        *,
        recurrence_key: str,
        branch_code: str | None = None,
        window_months: int = 12,
    ) -> dict[str, int]:
        filters = ["p.deleted_at IS NULL", "p.recurrence_key = %s"]
        params: list[Any] = [recurrence_key]

        if branch_code:
            filters.append("p.branch_code = %s")
            params.append(branch_code)

        where_clause = " AND ".join(filters)
        row = self.fetch_one(
            f"""
            SELECT COUNT(*) FILTER (
                       WHERE p.created_at >= NOW() - make_interval(months => %s)
                   )::int AS plans_in_window,
                   COUNT(*) FILTER (
                       WHERE p.status NOT IN ('completed', 'cancelled')
                   )::int AS open_plans,
                   COUNT(*)::int AS total_plans
              FROM quality.quality_action_plans p
             WHERE {where_clause}
            """,
            tuple([window_months, *params]),
        )

        return {
            "plans_in_window": int((row or {}).get("plans_in_window") or 0),
            "open_plans": int((row or {}).get("open_plans") or 0),
            "total_plans": int((row or {}).get("total_plans") or 0),
        }

    def fetch_knowledge_graph_paths(
        self,
        *,
        branch_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        from app.domain.services.pac_knowledge_graph_content_service import (
            PacKnowledgeGraphContentService,
        )

        row_limit = limit or PacKnowledgeGraphContentService.limit_int("maxRows", 200)
        filters = [
            "p.deleted_at IS NULL",
            "p.status NOT IN ('draft', 'cancelled')",
            "p.product_code IS NOT NULL",
            "TRIM(p.product_code) <> ''",
        ]
        params: list[Any] = []

        if branch_code:
            filters.append("p.branch_code = %s")
            params.append(branch_code)
        if product_code:
            filters.append("p.product_code = %s")
            params.append(product_code)

        where_clause = " AND ".join(filters)
        rows = self.fetch_all(
            f"""
            SELECT p.product_code,
                   p.failure_mode,
                   COALESCE(fw.root_cause, p.root_cause_category) AS root_cause,
                   a.description AS action_description,
                   COUNT(DISTINCT p.id)::int AS plan_count,
                   COUNT(DISTINCT p.id) FILTER (
                       WHERE p.effectiveness_status IN ('effective', 'partially_effective')
                   )::int AS effective_plan_count
              FROM quality.quality_action_plans p
              LEFT JOIN quality.quality_five_whys fw ON fw.plan_id = p.id
              LEFT JOIN quality.quality_actions a
                ON a.plan_id = p.id
               AND a.status = 'completed'
             WHERE {where_clause}
             GROUP BY p.product_code, p.failure_mode, root_cause, a.description
            HAVING COUNT(DISTINCT p.id) >= 1
             ORDER BY plan_count DESC, effective_plan_count DESC, p.product_code
             LIMIT %s
            """,
            tuple([*params, row_limit]),
        )
        return [dict(row) for row in rows]

    def list_solution_patterns(self, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT id, title, problem_category, failure_mode, root_cause_category,
                   symptom_tags, recommended_actions, actions_to_avoid,
                   evidence_summary, effectiveness_rate, usage_count, last_used_at
              FROM quality.quality_solution_patterns
             ORDER BY effectiveness_rate DESC NULLS LAST, usage_count DESC
             LIMIT %s
            """,
            (limit,),
        )
        return [self._serialize_pattern(row) for row in rows]

    def upsert_solution_pattern_from_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self.fetch_one(
            """
            SELECT p.id, p.code, p.title, p.problem_category, p.failure_mode,
                   p.root_cause_category, p.symptom_tags, p.effectiveness_status,
                   p.effectiveness_notes, fw.root_cause
              FROM quality.quality_action_plans p
              LEFT JOIN quality.quality_five_whys fw ON fw.plan_id = p.id
             WHERE p.id = %s
               AND p.deleted_at IS NULL
            """,
            (plan_id,),
        )
        if not plan:
            return None

        if plan.get("effectiveness_status") not in {"effective", "partially_effective"}:
            raise ValueError(
                "Promova apenas planos com eficácia effective ou partially_effective."
            )

        actions = self.fetch_all(
            """
            SELECT action_type, description
              FROM quality.quality_actions
             WHERE plan_id = %s
               AND status = 'completed'
             ORDER BY completed_at DESC NULLS LAST
            """,
            (plan_id,),
        )
        recommended = [a["description"] for a in actions if a.get("description")]
        if not recommended:
            raise ValueError("O plano precisa de ao menos uma ação concluída para virar padrão.")

        title = plan.get("title") or f"Padrão derivado de {plan.get('code')}"
        effectiveness_rate = 1.0 if plan.get("effectiveness_status") == "effective" else 0.6

        existing = self.fetch_one(
            """
            SELECT id, usage_count, effectiveness_rate
              FROM quality.quality_solution_patterns
             WHERE created_from_plan_id = %s
            """,
            (plan_id,),
        )
        if existing:
            row = self.execute_returning_one(
                """
                UPDATE quality.quality_solution_patterns
                   SET title = %s,
                       problem_category = %s,
                       failure_mode = %s,
                       root_cause_category = %s,
                       symptom_tags = %s,
                       recommended_actions = %s,
                       evidence_summary = %s,
                       effectiveness_rate = %s,
                       usage_count = usage_count + 1,
                       last_used_at = NOW(),
                       updated_at = NOW()
                 WHERE id = %s
                RETURNING id, title, problem_category, failure_mode, root_cause_category,
                          symptom_tags, recommended_actions, actions_to_avoid,
                          evidence_summary, effectiveness_rate, usage_count, last_used_at
                """,
                (
                    title,
                    plan.get("problem_category"),
                    plan.get("failure_mode"),
                    plan.get("root_cause_category") or plan.get("root_cause"),
                    plan.get("symptom_tags") or [],
                    recommended,
                    plan.get("effectiveness_notes"),
                    effectiveness_rate,
                    existing["id"],
                ),
            )
        else:
            row = self.execute_returning_one(
                """
                INSERT INTO quality.quality_solution_patterns (
                    title,
                    problem_category,
                    failure_mode,
                    root_cause_category,
                    symptom_tags,
                    recommended_actions,
                    evidence_summary,
                    effectiveness_rate,
                    usage_count,
                    last_used_at,
                    created_from_plan_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW(), %s)
                RETURNING id, title, problem_category, failure_mode, root_cause_category,
                          symptom_tags, recommended_actions, actions_to_avoid,
                          evidence_summary, effectiveness_rate, usage_count, last_used_at
                """,
                (
                    title,
                    plan.get("problem_category"),
                    plan.get("failure_mode"),
                    plan.get("root_cause_category") or plan.get("root_cause"),
                    plan.get("symptom_tags") or [],
                    recommended,
                    plan.get("effectiveness_notes"),
                    effectiveness_rate,
                    plan_id,
                ),
            )

        if not row:
            raise PluginsRepositoryError("Falha ao registrar padrão de solução.")
        return self._serialize_pattern(row)

    def increment_pattern_usage(self, pattern_ids: list[str]) -> None:
        if not pattern_ids:
            return
        self.execute(
            """
            UPDATE quality.quality_solution_patterns
               SET usage_count = usage_count + 1,
                   last_used_at = NOW(),
                   updated_at = NOW()
             WHERE id = ANY(%s::uuid[])
            """,
            (pattern_ids,),
        )

    def _serialize_pattern(self, row: dict[str, Any]) -> dict[str, Any]:
        result = serialize_row(row, id_keys=("id",)) or {}
        for key in ("symptom_tags", "recommended_actions", "actions_to_avoid"):
            if result.get(key) is None:
                result[key] = []
        if result.get("effectiveness_rate") is not None:
            result["effectiveness_rate"] = float(result["effectiveness_rate"])
        if result.get("usage_count") is not None:
            result["usage_count"] = int(result["usage_count"])
        last_used = result.get("last_used_at")
        if hasattr(last_used, "isoformat"):
            result["last_used_at"] = last_used.isoformat()
        return result
