"""Model / mode selector UI."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from app.ui.components import COLORS, indicator_dot, mode_label


class ModelSelector(ft.Container):
    def __init__(
        self,
        on_change: Callable[[str, str], None],
        models: Optional[list[dict]] = None,
    ):
        self.on_change = on_change
        self.models = models or []
        self.mode = "auto"
        self.model = "auto"
        self.mode_dd = ft.Dropdown(
            dense=True,
            value="auto",
            width=200,
            options=[
                ft.dropdown.Option("auto", mode_label("auto")),
                ft.dropdown.Option("local_only", mode_label("local_only")),
                ft.dropdown.Option("economy", mode_label("economy")),
                ft.dropdown.Option("manual", mode_label("manual")),
            ],
            on_change=self._mode_changed,
            border_color=COLORS["accent2"],
            color=COLORS["text"],
        )
        self.model_dd = ft.Dropdown(
            dense=True,
            value="auto",
            width=220,
            options=[ft.dropdown.Option("auto", "🤖 NEXUS AUTO")],
            on_change=self._model_changed,
            border_color=COLORS["accent2"],
            color=COLORS["text"],
            visible=False,
        )
        super().__init__(
            content=ft.Row(
                [self.mode_dd, self.model_dd],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    def set_models(self, models: list[dict]) -> None:
        self.models = models
        opts = [ft.dropdown.Option("auto", "🤖 NEXUS AUTO")]
        for m in models:
            label = f"{m.get('name')} • {m.get('display_location')}"
            opts.append(ft.dropdown.Option(m["id"], label))
        self.model_dd.options = opts
        self.update()

    def _mode_changed(self, e) -> None:
        self.mode = self.mode_dd.value or "auto"
        self.model_dd.visible = self.mode == "manual"
        if self.mode != "manual":
            self.model = "auto"
            self.model_dd.value = "auto"
        self.update()
        self.on_change(self.mode, self.model)

    def _model_changed(self, e) -> None:
        self.model = self.model_dd.value or "auto"
        self.on_change(self.mode, self.model)
