from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PacAuthenticatedActor:
    id: str
    name: str
    email: str


_PAC_ACTOR: ContextVar[PacAuthenticatedActor | None] = ContextVar(
    "pac_authenticated_actor",
    default=None,
)

PAC_GPT_AGENT_ACTOR = PacAuthenticatedActor(
    id="pac-gpt-agent",
    name="Agente GPT PAC",
    email="pac-gpt-agent@delpi.internal",
)


def set_pac_authenticated_actor(actor: PacAuthenticatedActor) -> Token:
    return _PAC_ACTOR.set(actor)


def reset_pac_authenticated_actor(token: Token) -> None:
    _PAC_ACTOR.reset(token)


def clear_pac_authenticated_actor() -> None:
    _PAC_ACTOR.set(None)


def get_pac_authenticated_actor() -> PacAuthenticatedActor | None:
    return _PAC_ACTOR.get()


def get_pac_authenticated_user_id() -> str:
    actor = get_pac_authenticated_actor()
    return actor.id if actor is not None else "unknown"


def actor_as_request_user(actor: PacAuthenticatedActor) -> Any:
    """Objeto mínimo compatível com `request.state.user` legado."""

    return actor
