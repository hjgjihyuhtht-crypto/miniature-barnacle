"""Model router facade used by API routes."""

from __future__ import annotations

from typing import Any, Optional

from backend.models import RoutingMode
from backend.services.intelligent_router import IntelligentRouter, RouteDecision
from backend.services.model_manager import ModelManager, get_model_manager


class ModelRouter:
    def __init__(self, manager: Optional[ModelManager] = None):
        self.manager = manager or get_model_manager()
        self.intelligent = IntelligentRouter(self.manager)

    def choose(
        self,
        model: str = "auto",
        messages: Optional[list[dict[str, str]]] = None,
        routing_mode: RoutingMode = RoutingMode.AUTO,
        allow_external_apis: bool = True,
        attachment_kinds: Optional[list[str]] = None,
        pinned_model: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> RouteDecision:
        return self.intelligent.choose(
            model=model,
            messages=messages or [],
            routing_mode=routing_mode,
            allow_external_apis=allow_external_apis,
            attachment_kinds=attachment_kinds,
            pinned_model=pinned_model,
            override_model=override_model,
        )

    def to_dict(self, decision: RouteDecision) -> dict[str, Any]:
        return {
            "selected_model": decision.selected_model,
            "mode": decision.mode,
            "task_type": decision.task_type,
            "location": decision.location,
            "display_name": decision.display_name,
            "reason": decision.reason,
        }


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
