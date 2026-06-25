"""Códigos RBAC do plugin Minha DELPI (api-delpi) — referência apenas.

A api-pac-quality autentica somente via `PAC_QUALITY_API_KEY`; não aplica RBAC
por usuário. Coordenação, filas e auditoria ficam no plugin.
"""

QUALITY_ACTION_PLANS_ACCESS = "quality-action-plans.access"
QUALITY_ACTION_PLANS_READ = "quality-action-plans.read"
QUALITY_ACTION_PLANS_WRITE = "quality-action-plans.write"
QUALITY_ACTION_PLANS_MANAGE = "quality-action-plans.manage"
QUALITY_ACTION_PLANS_CLOSE = "quality-action-plans.close"
QUALITY_ACTION_PLANS_VALIDATE_EFFECTIVENESS = "quality-action-plans.validate-effectiveness"
QUALITY_ACTION_PLANS_ADMIN = "quality-action-plans.admin"
