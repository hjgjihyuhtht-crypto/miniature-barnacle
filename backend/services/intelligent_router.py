"""Task analysis and intelligent routing for NEXUS AUTO."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from backend.config import load_model_capabilities, load_task_patterns
from backend.models import RoutingMode


@dataclass
class TaskAnalysis:
    task_type: str
    complexity: str
    needs_vision: bool
    needs_long_context: bool
    estimated_chars: int
    signals: list[str]


@dataclass
class RouteDecision:
    selected_model: str
    mode: str
    task_type: str
    location: str
    display_name: str
    reason: str
    alternatives: list[str]


class TaskAnalyzer:
    def __init__(self) -> None:
        self.patterns = load_task_patterns()

    def analyze(
        self,
        messages: list[dict[str, str]],
        attachment_kinds: Optional[list[str]] = None,
    ) -> TaskAnalysis:
        attachment_kinds = attachment_kinds or []
        text = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
        text_l = text.lower()
        scores: dict[str, int] = {}
        signals: list[str] = []
        for task, words in self.patterns.get("task_patterns", {}).items():
            score = 0
            for w in words:
                if w.lower() in text_l:
                    score += 1
                    signals.append(w)
            if score:
                scores[task] = score

        image_kinds = {"png", "jpg", "jpeg", "webp", "image"}
        needs_vision = bool(set(attachment_kinds) & image_kinds) or "vision" in scores
        if needs_vision:
            scores["vision"] = scores.get("vision", 0) + 2

        if any(k in attachment_kinds for k in ("pdf", "docx", "txt", "document")):
            scores["document_analysis"] = scores.get("document_analysis", 0) + 2

        task_type = "general_chat"
        if scores:
            task_type = max(scores, key=scores.get)  # type: ignore[arg-type]

        complexity = "medium"
        for level, words in self.patterns.get("complexity_signals", {}).items():
            if any(w.lower() in text_l for w in words):
                complexity = level
                break

        estimated = sum(len(m.get("content", "")) for m in messages)
        needs_long = estimated > 6000 or task_type == "long_context"

        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            needs_vision=needs_vision,
            needs_long_context=needs_long,
            estimated_chars=estimated,
            signals=signals[:8],
        )


class IntelligentRouter:
    def __init__(self, model_manager: Any):
        self.model_manager = model_manager
        self.analyzer = TaskAnalyzer()
        self.capabilities = load_model_capabilities()

    def _reason_for(self, task_type: str) -> str:
        labels = {
            "coding": "Tarefa identificada como programação.",
            "math": "Tarefa identificada como matemática.",
            "reasoning": "Tarefa identificada como raciocínio.",
            "technical": "Tarefa identificada como técnica.",
            "creative_writing": "Tarefa identificada como escrita criativa.",
            "translation": "Tarefa identificada como tradução.",
            "summarization": "Tarefa identificada como sumarização.",
            "document_analysis": "Tarefa identificada como análise de documento.",
            "research": "Tarefa identificada como pesquisa.",
            "vision": "Tarefa requer análise de imagem.",
            "voice": "Tarefa relacionada a áudio.",
            "long_context": "Tarefa requer contexto longo.",
            "general_chat": "Conversa geral.",
        }
        return labels.get(task_type, "Seleção automática com base na tarefa.")

    def _is_available(self, model_id: str, allow_external: bool) -> bool:
        meta = self.capabilities.get(model_id)
        if not meta:
            return False
        if meta.get("local"):
            return self.model_manager.local_available(model_id)
        if not allow_external:
            return False
        return self.model_manager.external_available(model_id)

    def _score_model(
        self,
        model_id: str,
        analysis: TaskAnalysis,
        mode: RoutingMode,
    ) -> float:
        meta = self.capabilities[model_id]
        score = 0.0
        task = analysis.task_type
        if meta.get(task):
            score += 10
        if task in (meta.get("preferred_tasks") or []):
            score += 5
        if analysis.needs_vision:
            if meta.get("vision"):
                score += 8
            else:
                score -= 20
        if analysis.needs_long_context and meta.get("long_context"):
            score += 3
        # Cost / economy
        cost = float(meta.get("cost_tier", 1))
        if mode == RoutingMode.ECONOMY:
            score += max(0, 5 - cost)
        if mode in (RoutingMode.LOCAL_ONLY, RoutingMode.ECONOMY) and meta.get("local"):
            score += 6
        # Prefer locals slightly in auto when available
        if mode == RoutingMode.AUTO and meta.get("local"):
            score += 2
        # Latency: lower tier is better
        latency = float(meta.get("latency_tier", 2))
        score += max(0, 3 - latency)
        if analysis.complexity == "high" and not meta.get("local"):
            score += 1
        return score

    def choose(
        self,
        model: str,
        messages: list[dict[str, str]],
        routing_mode: RoutingMode = RoutingMode.AUTO,
        allow_external_apis: bool = True,
        attachment_kinds: Optional[list[str]] = None,
        pinned_model: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> RouteDecision:
        analysis = self.analyzer.analyze(messages, attachment_kinds)

        # Manual / override / pin
        if override_model:
            return self._decision(override_model, routing_mode, analysis, "Seleção manual para esta mensagem.")
        if pinned_model:
            return self._decision(pinned_model, routing_mode, analysis, "Modelo fixado nesta conversa.")
        if routing_mode == RoutingMode.MANUAL or (model and model not in ("auto", "nexus-auto")):
            chosen = model if model not in ("auto", "nexus-auto") else "qwen-local"
            return self._decision(chosen, RoutingMode.MANUAL, analysis, "Seleção manual.")

        allow_external = allow_external_apis and routing_mode != RoutingMode.LOCAL_ONLY
        if routing_mode == RoutingMode.LOCAL_ONLY:
            allow_external = False

        candidates = []
        for mid, meta in self.capabilities.items():
            if routing_mode == RoutingMode.LOCAL_ONLY and not meta.get("local"):
                continue
            if not self._is_available(mid, allow_external):
                continue
            if analysis.needs_vision and not meta.get("vision"):
                # Keep as last-resort only if no vision models; skip for scoring prefer
                pass
            score = self._score_model(mid, analysis, routing_mode)
            candidates.append((score, mid))

        candidates.sort(reverse=True, key=lambda x: x[0])

        if analysis.needs_vision:
            vision_ok = [c for c in candidates if self.capabilities[c[1]].get("vision")]
            if vision_ok:
                candidates = vision_ok + [c for c in candidates if c not in vision_ok]
            elif routing_mode == RoutingMode.LOCAL_ONLY:
                raise RuntimeError(
                    "Essa tarefa não pode ser executada pelos recursos locais disponíveis."
                )

        if not candidates:
            if routing_mode == RoutingMode.LOCAL_ONLY:
                raise RuntimeError(
                    "Essa tarefa não pode ser executada pelos recursos locais disponíveis."
                )
            raise RuntimeError(
                "Nenhum modelo disponível. Configure modelos locais ou chaves de API."
            )

        selected = candidates[0][1]
        alts = [c[1] for c in candidates[1:6]]
        decision = self._decision(selected, routing_mode, analysis, self._reason_for(analysis.task_type))
        decision.alternatives = alts
        return decision

    def _decision(
        self,
        model_id: str,
        mode: RoutingMode | str,
        analysis: TaskAnalysis,
        reason: str,
    ) -> RouteDecision:
        meta = self.capabilities.get(model_id, {})
        location = "vps" if meta.get("local") else "api"
        mode_str = mode.value if isinstance(mode, RoutingMode) else str(mode)
        return RouteDecision(
            selected_model=model_id,
            mode=mode_str,
            task_type=analysis.task_type,
            location=location,
            display_name=meta.get("name", model_id),
            reason=reason,
            alternatives=[],
        )
