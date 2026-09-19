"""Memory settings / panel."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

import flet as ft

from app.ui.components import COLORS


class MemoryPanel(ft.Column):
    def __init__(
        self,
        on_refresh: Callable[[], Awaitable[list]],
        on_delete: Callable[[str], Awaitable[None]],
        on_delete_all: Callable[[], Awaitable[None]],
        on_toggle: Callable[[dict], None],
    ):
        self.on_refresh = on_refresh
        self.on_delete = on_delete
        self.on_delete_all = on_delete_all
        self.on_toggle = on_toggle
        self.enabled = ft.Switch(label="Memória ativada", value=True, on_change=self._changed)
        self.learn = ft.Switch(label="Aprender preferências", value=True, on_change=self._changed)
        self.ask = ft.Switch(label="Perguntar antes de salvar", value=True, on_change=self._changed)
        self.search = ft.TextField(label="Pesquisar", on_submit=lambda e: self.page.run_task(self.reload))
        self.list_view = ft.ListView(expand=True, spacing=8)
        super().__init__(
            controls=[
                ft.Text("Memória", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                self.enabled,
                self.learn,
                self.ask,
                ft.Row(
                    [
                        ft.ElevatedButton("Ver memórias", on_click=lambda e: self.page.run_task(self.reload)),
                        ft.ElevatedButton(
                            "Apagar todas",
                            bgcolor=COLORS["danger"],
                            on_click=lambda e: self.page.run_task(self._wipe),
                        ),
                    ]
                ),
                self.search,
                self.list_view,
            ],
            expand=True,
            spacing=10,
        )

    def _changed(self, e) -> None:
        self.on_toggle(
            {
                "memory_enabled": self.enabled.value,
                "learn_preferences": self.learn.value,
                "ask_before_save": self.ask.value,
            }
        )

    async def reload(self) -> None:
        items = await self.on_refresh()
        self.list_view.controls.clear()
        q = (self.search.value or "").lower()
        for item in items:
            if q and q not in (item.get("content") or "").lower():
                continue
            mid = item["id"]
            self.list_view.controls.append(
                ft.Container(
                    bgcolor=COLORS["panel"],
                    padding=10,
                    border_radius=8,
                    content=ft.Column(
                        [
                            ft.Text(item.get("type", ""), color=COLORS["accent"], size=12),
                            ft.Text(item.get("content", ""), color=COLORS["text"]),
                            ft.TextButton(
                                "Apagar",
                                on_click=lambda e, i=mid: self.page.run_task(self._delete_one, i),
                            ),
                        ]
                    ),
                )
            )
        self.update()

    async def _delete_one(self, mid: str) -> None:
        await self.on_delete(mid)
        await self.reload()

    async def _wipe(self) -> None:
        await self.on_delete_all()
        await self.reload()
