"""NEXUS AI — Flet application (Android / desktop)."""

from __future__ import annotations

import flet as ft

from app.database.db import LocalDB
from app.database.models import AppSettings
from app.ui.chat import ChatView
from app.ui.components import COLORS
from app.ui.memory_panel import MemoryPanel
from app.ui.settings import SettingsView
from app.ui.sidebar import Sidebar
from app.services.api_client import NexusAPIClient


def load_settings(db: LocalDB) -> AppSettings:
    return AppSettings(
        server_url=db.get_setting("server_url", "https://seu-dominio.com"),
        api_key=db.get_setting("api_key", ""),
        routing_mode=db.get_setting("routing_mode", "auto"),
        selected_model=db.get_setting("selected_model", "auto"),
        memory_enabled=db.get_setting("memory_enabled", "1") == "1",
        learn_preferences=db.get_setting("learn_preferences", "1") == "1",
        ask_before_save=db.get_setting("ask_before_save", "1") == "1",
        allow_external_apis=db.get_setting("allow_external_apis", "1") == "1",
        allow_memory_in_external=db.get_setting("allow_memory_in_external", "0") == "1",
        prefer_local_transcription=db.get_setting("prefer_local_transcription", "1") == "1",
    )


def save_settings(db: LocalDB, s: AppSettings) -> None:
    db.set_setting("server_url", s.server_url)
    db.set_setting("api_key", s.api_key)
    db.set_setting("routing_mode", s.routing_mode)
    db.set_setting("selected_model", s.selected_model)
    db.set_setting("memory_enabled", "1" if s.memory_enabled else "0")
    db.set_setting("learn_preferences", "1" if s.learn_preferences else "0")
    db.set_setting("ask_before_save", "1" if s.ask_before_save else "0")
    db.set_setting("allow_external_apis", "1" if s.allow_external_apis else "0")
    db.set_setting("allow_memory_in_external", "1" if s.allow_memory_in_external else "0")
    db.set_setting("prefer_local_transcription", "1" if s.prefer_local_transcription else "0")


def main(page: ft.Page) -> None:
    page.title = "NEXUS AI"
    page.bgcolor = COLORS["bg"]
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    db = LocalDB()
    settings = load_settings(db)

    body = ft.Container(expand=True)
    chat = ChatView(page, db, settings)

    def show_chat() -> None:
        body.content = chat
        page.update()
        page.run_task(chat.refresh_models)

    def new_chat() -> None:
        chat.new_conversation()
        sidebar.set_conversations(db.list_conversations())
        show_chat()

    def select_chat(cid: str) -> None:
        chat.load_conversation(cid)
        show_chat()

    def show_settings() -> None:
        def on_save(s: AppSettings) -> None:
            nonlocal settings
            settings = s
            chat.settings = s
            save_settings(db, s)
            show_chat()

        body.content = SettingsView(settings, on_save=on_save, on_back=show_chat)
        page.update()

    def show_memory() -> None:
        client = NexusAPIClient(settings.server_url, settings.api_key)

        async def refresh():
            return await client.list_memory()

        async def delete(mid: str):
            await client.delete_memory(mid)

        async def delete_all():
            await client.delete_all_memory()

        def on_toggle(flags: dict) -> None:
            settings.memory_enabled = flags.get("memory_enabled", True)
            settings.learn_preferences = flags.get("learn_preferences", True)
            settings.ask_before_save = flags.get("ask_before_save", True)
            save_settings(db, settings)

        panel = MemoryPanel(refresh, delete, delete_all, on_toggle)
        body.content = ft.Column(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_chat()),
                panel,
            ],
            expand=True,
        )
        page.update()
        page.run_task(panel.reload)

    sidebar = Sidebar(new_chat, select_chat, show_settings, show_memory)
    sidebar.set_conversations(db.list_conversations())

    page.add(
        ft.Row(
            [sidebar, body],
            expand=True,
            spacing=0,
        )
    )
    chat.new_conversation()
    show_chat()


if __name__ == "__main__":
    ft.app(target=main)
