"""Conversation sidebar."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from app.ui.components import COLORS


class Sidebar(ft.Container):
    def __init__(
        self,
        on_new: Callable[[], None],
        on_select: Callable[[str], None],
        on_settings: Callable[[], None],
        on_memory: Callable[[], None],
    ):
        self.on_new = on_new
        self.on_select = on_select
        self.on_settings = on_settings
        self.on_memory = on_memory
        self.list_view = ft.ListView(expand=True, spacing=4)
        super().__init__(
            width=260,
            bgcolor=COLORS["panel"],
            padding=12,
            content=ft.Column(
                [
                    ft.Text("NEXUS AI", size=22, weight=ft.FontWeight.BOLD, color=COLORS["accent"]),
                    ft.ElevatedButton("Nova conversa", icon=ft.Icons.ADD, on_click=lambda e: self.on_new()),
                    self.list_view,
                    ft.Divider(color=COLORS["muted"]),
                    ft.TextButton("🧠 Memória", on_click=lambda e: self.on_memory()),
                    ft.TextButton("⚙️ Configurações", on_click=lambda e: self.on_settings()),
                ],
                expand=True,
            ),
        )

    def set_conversations(self, items: list[dict]) -> None:
        self.list_view.controls.clear()
        for c in items:
            cid = c["id"]
            self.list_view.controls.append(
                ft.ListTile(
                    title=ft.Text(c.get("title") or "Conversa", color=COLORS["text"], size=13),
                    subtitle=ft.Text(c.get("model") or "", color=COLORS["muted"], size=11),
                    on_click=lambda e, i=cid: self.on_select(i),
                    dense=True,
                )
            )
        self.update()
