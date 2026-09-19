"""Settings screen."""

from __future__ import annotations

from typing import Callable

import flet as ft

from app.database.models import AppSettings
from app.ui.components import COLORS


class SettingsView(ft.Column):
    def __init__(self, settings: AppSettings, on_save: Callable[[AppSettings], None], on_back: Callable[[], None]):
        self.settings = settings
        self.on_save = on_save
        self.on_back = on_back
        self.server_url = ft.TextField(label="URL do NEXUS Backend", value=settings.server_url, color=COLORS["text"])
        self.api_key = ft.TextField(
            label="NEXUS API Key",
            value=settings.api_key,
            password=True,
            can_reveal_password=True,
            color=COLORS["text"],
        )
        self.allow_external = ft.Switch(label="Permitir APIs externas", value=settings.allow_external_apis)
        self.allow_mem_ext = ft.Switch(
            label="Permitir contexto da memória em APIs",
            value=settings.allow_memory_in_external,
        )
        self.local_stt = ft.Switch(
            label="Transcrição local quando disponível",
            value=settings.prefer_local_transcription,
        )
        self.memory_enabled = ft.Switch(label="Memória ativada", value=settings.memory_enabled)
        super().__init__(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.on_back()),
                        ft.Text("Configurações", size=22, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ]
                ),
                ft.Text("Servidor", color=COLORS["accent"], weight=ft.FontWeight.BOLD),
                self.server_url,
                self.api_key,
                ft.Text("Privacidade", color=COLORS["accent"], weight=ft.FontWeight.BOLD),
                self.memory_enabled,
                self.allow_external,
                self.allow_mem_ext,
                self.local_stt,
                ft.Text("Aparência / Chat", color=COLORS["accent"], weight=ft.FontWeight.BOLD),
                ft.Text("Tema escuro padrão do NEXUS AI", color=COLORS["muted"]),
                ft.ElevatedButton("Salvar", on_click=self._save),
            ],
            spacing=12,
        )

    def _save(self, e) -> None:
        self.settings.server_url = self.server_url.value or ""
        self.settings.api_key = self.api_key.value or ""
        self.settings.allow_external_apis = bool(self.allow_external.value)
        self.settings.allow_memory_in_external = bool(self.allow_mem_ext.value)
        self.settings.prefer_local_transcription = bool(self.local_stt.value)
        self.settings.memory_enabled = bool(self.memory_enabled.value)
        self.on_save(self.settings)
