from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.domain.services.five_whys_service import (
    five_whys_json,
    serialize_five_whys_row,
)
from app.domain.services.ishikawa_causes_service import (
    ishikawa_causes_json,
    serialize_ishikawa_row,
)
from app.domain.ports.quality_action_plan_repository_port import (
    PLAN_SELECT,
    QualityActionPlanRepositoryPort,
    serialize_plan_row,
    serialize_row,
)
from app.infrastructure.persistence.plugins.plugin_base_repository import (
    PluginBaseRepository,
    PluginsRepositoryError,
)

_TERMINAL_PLAN_STATUSES = frozenset({"completed", "cancelled"})


class PostgresQualityActionPlanRepository(PluginBaseRepository, QualityActionPlanRepositoryPort):
    def next_plan_code(self) -> str:
        row = self.execute_returning_one(
            """
            UPDATE quality.document_sequences
               SET current_value = current_value + 1,
                   updated_at = NOW()
             WHERE sequence_key = 'quality_action_plan'
               AND active = TRUE
            RETURNING prefix, current_value, padding_length
            """,
            auto_commit=False,
        )
        if not row:
            raise PluginsRepositoryError(
                "Sequência quality_action_plan não encontrada. Execute as migrations do plugin quality-action-plans."
            )

        year = datetime.now(timezone.utc).year
        padded = str(int(row["current_value"])).zfill(int(row["padding_length"]))
        return f"{row['prefix']}-{year}-{padded}"

    def create_plan(self, fields: dict[str, Any]) -> dict[str, Any]:
        code = self.next_plan_code()
        row = self.execute_returning_one(
            f"""
            INSERT INTO quality.quality_action_plans (
                code,
                title,
                customer_name,
                customer_code,
                customer_store,
                customer_contact,
                nonconformity_scope,
                customer_template,
                client_nc_registry,
                source_type,
                source_reference,
                product_code,
                product_description,
                batch_number,
                reported_problem,
                detected_at,
                reported_at,
                severity,
                status,
                created_by_user_id,
                owner_user_id,
                branch_code,
                department,
                problem_category,
                symptom_tags,
                root_cause_category,
                failure_mode,
                recurrence_key
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, code, status
            """,
            (
                code,
                fields["title"],
                fields.get("customer_name"),
                fields.get("customer_code"),
                fields.get("customer_store"),
                fields.get("customer_contact"),
                fields.get("nonconformity_scope", "external"),
                fields.get("customer_template", "generic"),
                fields.get("client_nc_registry"),
                fields.get("source_type"),
                fields.get("source_reference"),
                fields.get("product_code"),
                fields.get("product_description"),
                fields.get("batch_number"),
                fields.get("reported_problem"),
                fields.get("detected_at"),
                fields.get("reported_at"),
                fields.get("severity", "medium"),
                fields.get("status", "triage"),
                fields["created_by_user_id"],
                fields.get("owner_user_id"),
                fields.get("branch_code"),
                fields.get("department"),
                fields.get("problem_category"),
                fields.get("symptom_tags") or [],
                fields.get("root_cause_category"),
                fields.get("failure_mode"),
                fields.get("recurrence_key"),
            ),
            auto_commit=False,
        )
        if not row:
            self.rollback()
            raise PluginsRepositoryError("Falha ao criar plano de ação.")

        plan_id = str(row["id"])
        self.append_history(
            plan_id=plan_id,
            event_type="plan_created",
            created_by=fields["created_by_user_id"],
            new_value=code,
            comment="Plano de ação criado via API PAC.",
            auto_commit=False,
        )
        self.commit()
        return serialize_plan_row(self.get_plan_by_id(plan_id) or row)

    def get_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            f"""
            {PLAN_SELECT}
             WHERE p.id = %s
               AND p.deleted_at IS NULL
            """,
            (plan_id,),
        )
        return serialize_plan_row(row) if row else None

    def get_plan_detail(self, plan_id: str) -> dict[str, Any] | None:
        plan_row = self.fetch_one(
            f"""
            {PLAN_SELECT}
             WHERE p.id = %s AND p.deleted_at IS NULL
            """,
            (plan_id,),
        )
        if not plan_row:
            return None

        ishikawa = self.fetch_one(
            """
            SELECT id, plan_id, machine, method_process, material, manpower,
                   measurement, environment, notes, created_at, updated_at
              FROM quality.quality_ishikawa_analysis WHERE plan_id = %s
            """,
            (plan_id,),
        )
        five_whys = self.fetch_one(
            """
            SELECT id, plan_id, occurrence_whys, detection_whys,
                   root_cause, confidence_level, created_at, updated_at
              FROM quality.quality_five_whys WHERE plan_id = %s
            """,
            (plan_id,),
        )
        actions = self.fetch_all(
            """
            SELECT id, plan_id, action_type, description, responsible_user_id,
                   responsible_name, department, due_date, status,
                   evidence_required, cause_track, completed_at, created_at, updated_at
              FROM quality.quality_actions
             WHERE plan_id = %s
             ORDER BY due_date NULLS LAST, created_at ASC
            """,
            (plan_id,),
        )
        team_members = self.fetch_all(
            """
            SELECT id, plan_id, member_name, department, is_leader, sort_order, created_at
              FROM quality.quality_analysis_team_members
             WHERE plan_id = %s
             ORDER BY is_leader DESC, sort_order ASC, created_at ASC
            """,
            (plan_id,),
        )
        evidences = self.fetch_all(
            """
            SELECT id, plan_id, type, file_name, file_url, text_excerpt,
                   stored_name, mime_type, size_bytes, section, description,
                   knowledge_visible, uploaded_by, action_id, created_at
              FROM quality.quality_problem_evidences
             WHERE plan_id = %s
             ORDER BY created_at DESC
            """,
            (plan_id,),
        )
        history = self.fetch_all(
            """
            SELECT id, plan_id, event_type, old_value, new_value, comment,
                   created_by, created_at
              FROM quality.quality_action_history
             WHERE plan_id = %s
             ORDER BY created_at DESC
             LIMIT 100
            """,
            (plan_id,),
        )

        return {
            "plan": serialize_plan_row(plan_row),
            "ishikawa": serialize_ishikawa_row(ishikawa),
            "five_whys": serialize_five_whys_row(five_whys),
            "team_members": [
                serialize_row(row, id_keys=("id", "plan_id")) for row in team_members if row
            ],
            "evidences": [
                serialize_row(row, id_keys=("id", "plan_id", "action_id")) for row in evidences if row
            ],
            "actions": [
                serialize_row(row, id_keys=("id", "plan_id")) for row in actions if row
            ],
            "history": [
                serialize_row(row, id_keys=("id", "plan_id")) for row in history if row
            ],
        }

    def list_plans(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        product_code: str | None = None,
        customer_name: str | None = None,
        owner_user_id: str | None = None,
        branch_code: str | None = None,
        nonconformity_scope: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        filters = ["p.deleted_at IS NULL"]
        params: list[Any] = []

        if status:
            filters.append("p.status = %s")
            params.append(status)
        if severity:
            filters.append("p.severity = %s")
            params.append(severity)
        if product_code:
            filters.append("p.product_code = %s")
            params.append(product_code)
        if customer_name:
            filters.append("p.customer_name ILIKE %s")
            params.append(f"%{customer_name.strip()}%")
        if owner_user_id:
            filters.append("p.owner_user_id = %s")
            params.append(owner_user_id)
        if branch_code:
            filters.append("p.branch_code = %s")
            params.append(branch_code)
        if nonconformity_scope:
            filters.append("p.nonconformity_scope = %s")
            params.append(nonconformity_scope)

        where_clause = " AND ".join(filters)
        count_row = self.fetch_one(
            f"SELECT COUNT(*) AS total FROM quality.quality_action_plans p WHERE {where_clause}",
            tuple(params),
        )
        total = int(count_row["total"]) if count_row else 0
        offset = max(page - 1, 0) * page_size

        rows = self.fetch_all(
            f"""
            {PLAN_SELECT}
             WHERE {where_clause}
             ORDER BY p.created_at DESC
             LIMIT %s OFFSET %s
            """,
            tuple([*params, page_size, offset]),
        )

        return {
            "items": [serialize_plan_row(row) for row in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max((total + page_size - 1) // page_size, 1),
            },
        }

    def update_plan(self, plan_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get_plan_by_id(plan_id)
        if not current:
            return None

        allowed = {
            "title",
            "customer_name",
            "customer_code",
            "customer_store",
            "customer_contact",
            "nonconformity_scope",
            "source_type",
            "source_reference",
            "product_code",
            "product_description",
            "batch_number",
            "reported_problem",
            "detected_at",
            "reported_at",
            "severity",
            "owner_user_id",
            "branch_code",
            "department",
            "problem_category",
            "symptom_tags",
            "root_cause_category",
            "failure_mode",
            "recurrence_key",
            "customer_template",
            "client_nc_registry",
            "effectiveness_status",
            "effectiveness_verified_at",
            "effectiveness_notes",
        }
        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed and value is not None
        }
        if not updates:
            return current

        set_parts = [f"{column} = %s" for column in updates]
        set_parts.append("updated_at = NOW()")
        params = list(updates.values()) + [plan_id]

        self.execute(
            f"""
            UPDATE quality.quality_action_plans
               SET {", ".join(set_parts)}
             WHERE id = %s
               AND deleted_at IS NULL
            """,
            tuple(params),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="plan_updated",
            created_by=fields.get("updated_by_user_id", "system"),
            comment="Plano atualizado via API PAC.",
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def update_plan_status(
        self,
        plan_id: str,
        *,
        status: str,
        updated_by: str,
        comment: str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get_plan_by_id(plan_id)
        if not current:
            return None

        closed_at_sql = ", closed_at = NOW()" if status == "completed" else ""
        self.execute(
            f"""
            UPDATE quality.quality_action_plans
               SET status = %s,
                   updated_at = NOW()
                   {closed_at_sql}
             WHERE id = %s
               AND deleted_at IS NULL
            """,
            (status, plan_id),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="status_changed",
            created_by=updated_by,
            old_value=current.get("status"),
            new_value=status,
            comment=comment,
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def append_history(
        self,
        *,
        plan_id: str,
        event_type: str,
        created_by: str,
        old_value: str | None = None,
        new_value: str | None = None,
        comment: str | None = None,
        auto_commit: bool = True,
    ) -> None:
        self.execute(
            """
            INSERT INTO quality.quality_action_history (
                plan_id,
                event_type,
                old_value,
                new_value,
                comment,
                created_by
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (plan_id, event_type, old_value, new_value, comment, created_by),
            auto_commit=auto_commit,
        )

    def _plan_exists(self, plan_id: str) -> bool:
        row = self.fetch_one(
            """
            SELECT id FROM quality.quality_action_plans
             WHERE id = %s AND deleted_at IS NULL
            """,
            (plan_id,),
        )
        return row is not None

    def action_belongs_to_plan(self, plan_id: str, action_id: str) -> bool:
        row = self.fetch_one(
            "SELECT id FROM quality.quality_actions WHERE id = %s AND plan_id = %s",
            (action_id, plan_id),
        )
        return row is not None

    def upsert_ishikawa(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        causes_json = ishikawa_causes_json(fields)
        row = self.execute_returning_one(
            """
            INSERT INTO quality.quality_ishikawa_analysis (
                plan_id, machine, method_process, material, manpower, measurement, environment, notes
            ) VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
            ON CONFLICT (plan_id) DO UPDATE SET
                machine = EXCLUDED.machine,
                method_process = EXCLUDED.method_process,
                material = EXCLUDED.material,
                manpower = EXCLUDED.manpower,
                measurement = EXCLUDED.measurement,
                environment = EXCLUDED.environment,
                notes = EXCLUDED.notes,
                updated_at = NOW()
            RETURNING id, plan_id, machine, method_process, material, manpower,
                      measurement, environment, notes, created_at, updated_at
            """,
            (
                plan_id,
                causes_json["machine"],
                causes_json["method_process"],
                causes_json["material"],
                causes_json["manpower"],
                causes_json["measurement"],
                causes_json["environment"],
                fields.get("notes"),
            ),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="ishikawa_updated",
            created_by=updated_by,
            auto_commit=False,
        )
        self.commit()
        return serialize_ishikawa_row(row)

    def get_ishikawa(self, plan_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            """
            SELECT id, plan_id, machine, method_process, material, manpower,
                   measurement, environment, notes, created_at, updated_at
              FROM quality.quality_ishikawa_analysis
             WHERE plan_id = %s
            """,
            (plan_id,),
        )
        return serialize_ishikawa_row(row)

    def upsert_five_whys(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        whys_json = five_whys_json(fields)
        row = self.execute_returning_one(
            """
            INSERT INTO quality.quality_five_whys (
                plan_id, occurrence_whys, detection_whys, root_cause, confidence_level
            ) VALUES (%s, %s::jsonb, %s::jsonb, %s, %s)
            ON CONFLICT (plan_id) DO UPDATE SET
                occurrence_whys = EXCLUDED.occurrence_whys,
                detection_whys = EXCLUDED.detection_whys,
                root_cause = EXCLUDED.root_cause,
                confidence_level = EXCLUDED.confidence_level,
                updated_at = NOW()
            RETURNING id, plan_id, occurrence_whys, detection_whys,
                      root_cause, confidence_level, created_at, updated_at
            """,
            (
                plan_id,
                whys_json["occurrence_whys"],
                whys_json["detection_whys"],
                fields.get("root_cause"),
                fields.get("confidence_level"),
            ),
            auto_commit=False,
        )
        if fields.get("root_cause"):
            self.execute(
                """
                UPDATE quality.quality_action_plans
                   SET root_cause_category = COALESCE(root_cause_category, 'processo'),
                       updated_at = NOW()
                 WHERE id = %s
                """,
                (plan_id,),
                auto_commit=False,
            )
        self.append_history(
            plan_id=plan_id,
            event_type="five_whys_updated",
            created_by=updated_by,
            new_value=fields.get("root_cause"),
            auto_commit=False,
        )
        self.commit()
        return serialize_five_whys_row(row)

    def get_five_whys(self, plan_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            """
            SELECT id, plan_id, occurrence_whys, detection_whys,
                   root_cause, confidence_level, created_at, updated_at
              FROM quality.quality_five_whys
             WHERE plan_id = %s
            """,
            (plan_id,),
        )
        return serialize_five_whys_row(row)

    def create_actions(
        self, plan_id: str, actions: list[dict[str, Any]], *, created_by: str
    ) -> list[dict[str, Any]] | None:
        if not self._plan_exists(plan_id):
            return None
        if not actions:
            return []

        created: list[dict[str, Any]] = []
        for action in actions:
            row = self.execute_returning_one(
                """
                INSERT INTO quality.quality_actions (
                    plan_id, action_type, description, responsible_user_id,
                    responsible_name, department, due_date, status, evidence_required, cause_track
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, plan_id, action_type, description, responsible_user_id,
                          responsible_name, department, due_date, status,
                          evidence_required, cause_track, completed_at, created_at, updated_at
                """,
                (
                    plan_id,
                    action["action_type"],
                    action["description"],
                    action.get("responsible_user_id"),
                    action.get("responsible_name"),
                    action.get("department"),
                    action.get("due_date"),
                    action.get("status", "pending"),
                    action.get("evidence_required", False),
                    action.get("cause_track"),
                ),
                auto_commit=False,
            )
            if row:
                created.append(serialize_row(row, id_keys=("id", "plan_id")) or {})
                self.append_history(
                    plan_id=plan_id,
                    event_type="action_created",
                    created_by=created_by,
                    new_value=action["description"][:200],
                    auto_commit=False,
                )
        self.commit()
        return created

    def list_actions(self, plan_id: str) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT id, plan_id, action_type, description, responsible_user_id,
                   responsible_name, department, due_date, status,
                   evidence_required, cause_track, completed_at, created_at, updated_at
              FROM quality.quality_actions
             WHERE plan_id = %s
             ORDER BY due_date NULLS LAST, created_at ASC
            """,
            (plan_id,),
        )
        return [serialize_row(row, id_keys=("id", "plan_id")) for row in rows if row]

    def update_action(
        self, plan_id: str, action_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        allowed = {
            "action_type",
            "description",
            "responsible_user_id",
            "responsible_name",
            "department",
            "due_date",
            "status",
            "evidence_required",
            "cause_track",
        }
        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed and (value is not None or key == "cause_track")
        }
        if not updates:
            rows = self.list_actions(plan_id)
            return next((r for r in rows if r and r.get("id") == action_id), None)

        set_parts = [f"{column} = %s" for column in updates]
        params: list[Any] = list(updates.values())
        if updates.get("status") == "completed":
            set_parts.append("completed_at = NOW()")
        set_parts.append("updated_at = NOW()")
        params.extend([action_id, plan_id])

        row = self.execute_returning_one(
            f"""
            UPDATE quality.quality_actions
               SET {", ".join(set_parts)}
             WHERE id = %s AND plan_id = %s
            RETURNING id, plan_id, action_type, description, responsible_user_id,
                      responsible_name, department, due_date, status,
                      evidence_required, cause_track, completed_at, created_at, updated_at
            """,
            tuple(params),
            auto_commit=False,
        )
        if not row:
            self.rollback()
            return None

        event = "action_completed" if fields.get("status") == "completed" else "action_updated"
        self.append_history(
            plan_id=plan_id,
            event_type=event,
            created_by=updated_by,
            auto_commit=False,
        )
        self.commit()
        return serialize_row(row, id_keys=("id", "plan_id"))

    def delete_action(
        self, plan_id: str, action_id: str, *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self.action_belongs_to_plan(plan_id, action_id):
            return None

        row = self.fetch_one(
            """
            SELECT id, description
              FROM quality.quality_actions
             WHERE id = %s AND plan_id = %s
            """,
            (action_id, plan_id),
        )
        if not row:
            return None

        self.execute(
            "DELETE FROM quality.quality_actions WHERE id = %s AND plan_id = %s",
            (action_id, plan_id),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="action_deleted",
            created_by=updated_by,
            old_value=(row.get("description") or "")[:200],
            auto_commit=False,
        )
        self.commit()
        return {"id": str(action_id), "deleted": True}

    def record_effectiveness_review(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET effectiveness_status = %s,
                   effectiveness_verified_at = NOW(),
                   effectiveness_notes = %s,
                   effectiveness_approval_status = NULL,
                   effectiveness_proposed_status = NULL,
                   effectiveness_submitted_at = NULL,
                   effectiveness_submitted_by = NULL,
                   effectiveness_reviewed_at = NOW(),
                   effectiveness_reviewed_by = %s,
                   effectiveness_rejection_reason = NULL,
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (
                fields["effectiveness_status"],
                fields.get("notes"),
                updated_by,
                plan_id,
            ),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="effectiveness_reviewed",
            created_by=updated_by,
            new_value=fields["effectiveness_status"],
            comment=fields.get("notes"),
            auto_commit=False,
        )
        self.append_audit_log(
            entity_type="quality_action_plan",
            entity_id=plan_id,
            event_type="effectiveness_reviewed",
            actor_user_id=updated_by,
            payload={
                "effectiveness_status": fields["effectiveness_status"],
                "notes": fields.get("notes"),
            },
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def submit_effectiveness_review(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        current = self.get_plan_by_id(plan_id)
        if current is None:
            return None
        if current.get("effectiveness_approval_status") == "pending_review":
            raise ValueError("Já existe submissão de eficácia aguardando aprovação.")

        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET effectiveness_proposed_status = %s,
                   effectiveness_approval_status = 'pending_review',
                   effectiveness_notes = %s,
                   effectiveness_submitted_at = NOW(),
                   effectiveness_submitted_by = %s,
                   effectiveness_reviewed_at = NULL,
                   effectiveness_reviewed_by = NULL,
                   effectiveness_rejection_reason = NULL,
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (
                fields["effectiveness_status"],
                fields.get("notes"),
                updated_by,
                plan_id,
            ),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="effectiveness_submitted",
            created_by=updated_by,
            new_value=fields["effectiveness_status"],
            comment=fields.get("notes"),
            auto_commit=False,
        )
        self.append_audit_log(
            entity_type="quality_action_plan",
            entity_id=plan_id,
            event_type="effectiveness_submitted",
            actor_user_id=updated_by,
            payload={
                "proposed_status": fields["effectiveness_status"],
                "notes": fields.get("notes"),
            },
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def approve_effectiveness_review(
        self, plan_id: str, *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        current = self.get_plan_by_id(plan_id)
        if current is None:
            return None
        if current.get("effectiveness_approval_status") != "pending_review":
            raise ValueError("Não há submissão de eficácia pendente de aprovação.")
        proposed = current.get("effectiveness_proposed_status")
        if not proposed:
            raise ValueError("Submissão sem resultado proposto.")

        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET effectiveness_status = %s,
                   effectiveness_verified_at = NOW(),
                   effectiveness_approval_status = 'approved',
                   effectiveness_reviewed_at = NOW(),
                   effectiveness_reviewed_by = %s,
                   effectiveness_rejection_reason = NULL,
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (proposed, updated_by, plan_id),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="effectiveness_reviewed",
            created_by=updated_by,
            new_value=proposed,
            comment=current.get("effectiveness_notes"),
            auto_commit=False,
        )
        self.append_audit_log(
            entity_type="quality_action_plan",
            entity_id=plan_id,
            event_type="effectiveness_approved",
            actor_user_id=updated_by,
            payload={
                "effectiveness_status": proposed,
                "submitted_by": current.get("effectiveness_submitted_by"),
            },
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def reject_effectiveness_review(
        self, plan_id: str, *, reason: str, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        current = self.get_plan_by_id(plan_id)
        if current is None:
            return None
        if current.get("effectiveness_approval_status") != "pending_review":
            raise ValueError("Não há submissão de eficácia pendente de aprovação.")

        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET effectiveness_approval_status = 'rejected',
                   effectiveness_reviewed_at = NOW(),
                   effectiveness_reviewed_by = %s,
                   effectiveness_rejection_reason = %s,
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (updated_by, reason, plan_id),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="effectiveness_approval_rejected",
            created_by=updated_by,
            new_value=current.get("effectiveness_proposed_status"),
            comment=reason,
            auto_commit=False,
        )
        self.append_audit_log(
            entity_type="quality_action_plan",
            entity_id=plan_id,
            event_type="effectiveness_approval_rejected",
            actor_user_id=updated_by,
            payload={
                "proposed_status": current.get("effectiveness_proposed_status"),
                "reason": reason,
                "submitted_by": current.get("effectiveness_submitted_by"),
            },
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def reopen_plan(
        self,
        plan_id: str,
        *,
        target_status: str,
        reason: str,
        updated_by: str,
    ) -> dict[str, Any] | None:
        current = self.get_plan_by_id(plan_id)
        if not current:
            return None

        previous_status = current.get("status")
        if previous_status not in _TERMINAL_PLAN_STATUSES:
            raise ValueError(
                "Somente planos concluídos ou cancelados podem ser reabertos."
            )
        if target_status in _TERMINAL_PLAN_STATUSES:
            raise ValueError("Status alvo inválido para reabertura.")

        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET status = %s,
                   closed_at = NULL,
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (target_status, plan_id),
            auto_commit=False,
        )
        self.append_history(
            plan_id=plan_id,
            event_type="plan_reopened",
            created_by=updated_by,
            old_value=previous_status,
            new_value=target_status,
            comment=reason,
            auto_commit=False,
        )
        self.append_audit_log(
            entity_type="quality_action_plan",
            entity_id=plan_id,
            event_type="plan_reopened",
            actor_user_id=updated_by,
            payload={
                "previous_status": previous_status,
                "target_status": target_status,
                "reason": reason,
            },
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_by_id(plan_id)

    def append_audit_log(
        self,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor_user_id: str,
        payload: dict[str, Any] | None = None,
        auto_commit: bool = True,
    ) -> None:
        self.execute(
            """
            INSERT INTO quality.quality_audit_log (
                entity_type, entity_id, event_type, payload, actor_user_id
            ) VALUES (%s, %s, %s, %s::jsonb, %s)
            """,
            (
                entity_type,
                entity_id,
                event_type,
                json.dumps(payload or {}),
                actor_user_id,
            ),
            auto_commit=auto_commit,
        )

    def list_actions_due_within_days(self, *, days_ahead: int = 2) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT a.id AS action_id,
                   a.plan_id,
                   a.description,
                   a.due_date,
                   a.responsible_user_id,
                   p.code AS plan_code,
                   p.title AS plan_title
              FROM quality.quality_actions a
              JOIN quality.quality_action_plans p ON p.id = a.plan_id
             WHERE p.deleted_at IS NULL
               AND a.status NOT IN ('completed', 'cancelled')
               AND a.due_date IS NOT NULL
               AND a.due_date > CURRENT_DATE
               AND a.due_date <= CURRENT_DATE + make_interval(days => %s)
               AND a.responsible_user_id IS NOT NULL
               AND trim(a.responsible_user_id) <> ''
             ORDER BY a.due_date ASC, p.code ASC
            """,
            (days_ahead,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            due_date = row.get("due_date")
            result.append(
                {
                    "action_id": str(row["action_id"]),
                    "plan_id": str(row["plan_id"]),
                    "description": row.get("description"),
                    "due_date": due_date,
                    "responsible_user_id": row.get("responsible_user_id"),
                    "plan_code": row.get("plan_code"),
                    "plan_title": row.get("plan_title"),
                }
            )
        return result

    def list_stalled_critical_plans(self, *, stall_days: int = 5) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT p.id,
                   p.code,
                   p.title,
                   p.owner_user_id,
                   p.status,
                   p.updated_at,
                   EXTRACT(DAY FROM (NOW() - p.updated_at))::int AS days_without_update
              FROM quality.quality_action_plans p
             WHERE p.deleted_at IS NULL
               AND p.status NOT IN ('completed', 'cancelled')
               AND p.severity = 'critical'
               AND p.updated_at < NOW() - make_interval(days => %s)
             ORDER BY p.updated_at ASC, p.code ASC
            """,
            (stall_days,),
        )
        return [
            {
                "id": str(row["id"]),
                "code": row.get("code"),
                "title": row.get("title"),
                "owner_user_id": row.get("owner_user_id"),
                "status": row.get("status"),
                "updated_at": row.get("updated_at"),
                "days_without_update": int(row.get("days_without_update") or 0),
            }
            for row in rows
        ]

    def notification_already_sent(self, notification_key: str) -> bool:
        row = self.fetch_one(
            """
            SELECT 1 AS found
              FROM quality.quality_notification_dispatches
             WHERE notification_key = %s
            """,
            (notification_key,),
        )
        return row is not None

    def record_notification_dispatch(
        self,
        *,
        notification_key: str,
        event_type: str,
        recipient_user_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
    ) -> None:
        self.execute(
            """
            INSERT INTO quality.quality_notification_dispatches (
                notification_key, event_type, recipient_user_id, entity_type, entity_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (notification_key) DO NOTHING
            """,
            (
                notification_key,
                event_type,
                recipient_user_id,
                entity_type,
                entity_id,
            ),
        )

    def upsert_rnc_8d_report(
        self, plan_id: str, fields: dict[str, Any], *, updated_by: str
    ) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None

        template_payload = fields.get("template_payload") or {}
        self.execute(
            """
            UPDATE quality.quality_action_plans
               SET customer_template = COALESCE(%s, customer_template),
                   client_nc_registry = COALESCE(%s, client_nc_registry),
                   customer_name = COALESCE(%s, customer_name),
                   customer_contact = COALESCE(%s, customer_contact),
                   product_code = COALESCE(%s, product_code),
                   product_description = COALESCE(%s, product_description),
                   batch_number = COALESCE(%s, batch_number),
                   reported_problem = COALESCE(%s, reported_problem),
                   template_payload = COALESCE(%s::jsonb, template_payload),
                   updated_at = NOW()
             WHERE id = %s AND deleted_at IS NULL
            """,
            (
                fields.get("customer_template", "rnc_8d"),
                fields.get("client_nc_registry"),
                fields.get("customer_name"),
                fields.get("customer_contact"),
                fields.get("product_code"),
                fields.get("product_description"),
                fields.get("batch_number"),
                fields.get("reported_problem"),
                json.dumps(template_payload) if template_payload else None,
                plan_id,
            ),
            auto_commit=False,
        )

        team_members = fields.get("team_members")
        if team_members is not None:
            self.execute(
                "DELETE FROM quality.quality_analysis_team_members WHERE plan_id = %s",
                (plan_id,),
                auto_commit=False,
            )
            for index, member in enumerate(team_members):
                self.execute(
                    """
                    INSERT INTO quality.quality_analysis_team_members (
                        plan_id, member_name, department, is_leader, sort_order
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        plan_id,
                        member.get("member_name") or member.get("name"),
                        member.get("department"),
                        bool(member.get("is_leader")),
                        member.get("sort_order", index),
                    ),
                    auto_commit=False,
                )

        self.append_history(
            plan_id=plan_id,
            event_type="plan_updated",
            created_by=updated_by,
            comment="Relatório 8D atualizado via API PAC.",
            auto_commit=False,
        )
        self.commit()
        return self.get_plan_detail(plan_id)

    def list_evidences(self, plan_id: str) -> list[dict[str, Any]]:
        if not self._plan_exists(plan_id):
            return []
        rows = self.fetch_all(
            """
            SELECT id, plan_id, type, file_name, file_url, text_excerpt,
                   stored_name, mime_type, size_bytes, section, description,
                   knowledge_visible, uploaded_by, action_id, created_at
              FROM quality.quality_problem_evidences
             WHERE plan_id = %s
             ORDER BY created_at DESC
            """,
            (plan_id,),
        )
        return [serialize_row(row, id_keys=("id", "plan_id", "action_id")) or {} for row in rows if row]

    def get_evidence(self, plan_id: str, evidence_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            """
            SELECT id, plan_id, type, file_name, file_url, text_excerpt,
                   stored_name, mime_type, size_bytes, section, description,
                   knowledge_visible, uploaded_by, action_id, created_at
              FROM quality.quality_problem_evidences
             WHERE id = %s AND plan_id = %s
            """,
            (evidence_id, plan_id),
        )
        return serialize_row(row, id_keys=("id", "plan_id", "action_id")) if row else None

    def create_evidence(self, plan_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        if not self._plan_exists(plan_id):
            return None
        action_id = fields.get("action_id")
        if action_id and not self.action_belongs_to_plan(plan_id, str(action_id)):
            return None
        row = self.execute_returning_one(
            """
            INSERT INTO quality.quality_problem_evidences (
                plan_id, type, file_name, file_url, text_excerpt,
                stored_name, mime_type, size_bytes, section, description,
                knowledge_visible, uploaded_by, action_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, plan_id, type, file_name, file_url, text_excerpt,
                      stored_name, mime_type, size_bytes, section, description,
                      knowledge_visible, uploaded_by, action_id, created_at
            """,
            (
                plan_id,
                fields["type"],
                fields.get("file_name"),
                fields.get("file_url"),
                fields.get("text_excerpt"),
                fields.get("stored_name"),
                fields.get("mime_type"),
                fields.get("size_bytes"),
                fields.get("section", "general"),
                fields.get("description"),
                fields.get("knowledge_visible", True),
                fields["uploaded_by"],
                action_id,
            ),
            auto_commit=True,
        )
        return serialize_row(row, id_keys=("id", "plan_id", "action_id")) if row else None

    def delete_evidence(self, plan_id: str, evidence_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            """
            SELECT id, plan_id, stored_name
              FROM quality.quality_problem_evidences
             WHERE id = %s AND plan_id = %s
            """,
            (evidence_id, plan_id),
        )
        if not row:
            return None
        self.execute(
            "DELETE FROM quality.quality_problem_evidences WHERE id = %s AND plan_id = %s",
            (evidence_id, plan_id),
            auto_commit=True,
        )
        return serialize_row(row, id_keys=("id", "plan_id"))

    def list_history(self, plan_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT id, plan_id, event_type, old_value, new_value, comment,
                   created_by, created_at
              FROM quality.quality_action_history
             WHERE plan_id = %s
             ORDER BY created_at DESC
             LIMIT %s
            """,
            (plan_id, limit),
        )
        return [serialize_row(row, id_keys=("id", "plan_id")) for row in rows if row]

    def list_plan_audit_log(
        self,
        plan_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        if not self._plan_exists(plan_id):
            return {
                "items": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": 0,
                    "total_pages": 1,
                },
            }

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        count_row = self.fetch_one(
            """
            SELECT COUNT(*)::int AS total
              FROM quality.quality_audit_log
             WHERE entity_type = 'quality_action_plan'
               AND entity_id = %s
            """,
            (plan_id,),
        )
        total = int((count_row or {}).get("total") or 0)
        offset = (page - 1) * page_size
        rows = self.fetch_all(
            """
            SELECT id,
                   entity_type,
                   entity_id,
                   event_type,
                   payload,
                   actor_user_id,
                   created_at
              FROM quality.quality_audit_log
             WHERE entity_type = 'quality_action_plan'
               AND entity_id = %s
             ORDER BY created_at DESC
             LIMIT %s OFFSET %s
            """,
            (plan_id, page_size, offset),
        )
        items: list[dict[str, Any]] = []
        for row in rows:
            created_at = row.get("created_at")
            items.append(
                {
                    "id": str(row["id"]),
                    "event_type": row.get("event_type"),
                    "payload": row.get("payload") or {},
                    "actor_user_id": row.get("actor_user_id"),
                    "created_at": (
                        created_at.isoformat()
                        if isinstance(created_at, datetime)
                        else created_at
                    ),
                }
            )
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max((total + page_size - 1) // page_size, 1),
            },
        }

    def list_pending_effectiveness_reviews(
        self, *, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        count_row = self.fetch_one(
            """
            SELECT COUNT(*) AS total
              FROM quality.quality_action_plans p
             WHERE p.deleted_at IS NULL
               AND p.effectiveness_approval_status = 'pending_review'
            """,
            (),
        )
        total = int(count_row["total"]) if count_row else 0
        offset = (page - 1) * page_size
        rows = self.fetch_all(
            f"""
            {PLAN_SELECT}
             WHERE p.deleted_at IS NULL
               AND p.effectiveness_approval_status = 'pending_review'
             ORDER BY p.effectiveness_submitted_at ASC NULLS LAST, p.created_at ASC
             LIMIT %s OFFSET %s
            """,
            (page_size, offset),
        )
        return {
            "items": [serialize_plan_row(row) for row in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max((total + page_size - 1) // page_size, 1),
            },
        }

    def get_dashboard_summary(self, *, branch_code: str | None = None) -> dict[str, Any]:
        branch_filter = ""
        params: list[Any] = []
        if branch_code:
            branch_filter = " AND branch_code = %s"
            params = [branch_code]

        row = self.fetch_one(
            f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND status NOT IN ('completed', 'cancelled')
                      {branch_filter}
                ) AS open_plans,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND status NOT IN ('completed', 'cancelled')
                      AND severity = 'critical'
                      {branch_filter}
                ) AS critical_open,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND status = 'waiting_validation'
                      {branch_filter}
                ) AS waiting_validation,
                COUNT(*) FILTER (
                    WHERE deleted_at IS NULL
                      AND status = 'completed'
                      AND closed_at >= date_trunc('month', NOW())
                      {branch_filter}
                ) AS completed_this_month
              FROM quality.quality_action_plans
              WHERE deleted_at IS NULL
              {branch_filter}
            """,
            tuple(params),
        )
        overdue_row = self.fetch_one(
            f"""
            SELECT COUNT(*) AS overdue_actions
              FROM quality.quality_actions a
              JOIN quality.quality_action_plans p ON p.id = a.plan_id
             WHERE p.deleted_at IS NULL
               AND a.status NOT IN ('completed', 'cancelled')
               AND a.due_date < CURRENT_DATE
               {branch_filter.replace("branch_code", "p.branch_code") if branch_filter else ""}
            """,
            tuple(params),
        )
        overdue_plans_row = self.fetch_one(
            f"""
            SELECT COUNT(DISTINCT p.id) AS overdue_plans
              FROM quality.quality_action_plans p
              JOIN quality.quality_actions a ON a.plan_id = p.id
             WHERE p.deleted_at IS NULL
               AND p.status NOT IN ('completed', 'cancelled')
               AND a.status NOT IN ('completed', 'cancelled')
               AND a.due_date < CURRENT_DATE
               {branch_filter.replace("branch_code", "p.branch_code") if branch_filter else ""}
            """,
            tuple(params),
        )
        result = {
            "open_plans": int((row or {}).get("open_plans") or 0),
            "critical_open": int((row or {}).get("critical_open") or 0),
            "waiting_validation": int((row or {}).get("waiting_validation") or 0),
            "completed_this_month": int((row or {}).get("completed_this_month") or 0),
            "overdue_actions": int((overdue_row or {}).get("overdue_actions") or 0),
            "overdue_plans": int((overdue_plans_row or {}).get("overdue_plans") or 0),
        }
        if branch_code:
            result["branch_code"] = branch_code
            return result

        by_branch_rows = self.fetch_all(
            """
            SELECT branch_code,
                   COUNT(*) FILTER (
                       WHERE status NOT IN ('completed', 'cancelled')
                   ) AS open_plans,
                   COUNT(*) FILTER (
                       WHERE status NOT IN ('completed', 'cancelled')
                         AND severity = 'critical'
                   ) AS critical_open
              FROM quality.quality_action_plans
             WHERE deleted_at IS NULL
               AND branch_code IS NOT NULL
             GROUP BY branch_code
             ORDER BY branch_code
            """
        )
        result["by_branch"] = [
            {
                "branch_code": row["branch_code"],
                "open_plans": int(row.get("open_plans") or 0),
                "critical_open": int(row.get("critical_open") or 0),
            }
            for row in by_branch_rows
            if row.get("branch_code")
        ]
        return result
