"""Shared UI components."""

from __future__ import annotations

import flet as ft


COLORS = {
    "bg": "#0B1220",
    "panel": "#121A2B",
    "accent": "#3DDC97",
    "accent2": "#4C8DFF",
    "text": "#E8EEF9",
    "muted": "#9AA8C7",
    "danger": "#FF5C7A",
    "local": "#3DDC97",
    "api": "#4C8DFF",
    "offline": "#FF5C7A",
}


def indicator_dot(kind: str) -> ft.Container:
    color = COLORS["local"]
    if kind == "api":
        color = COLORS["api"]
    elif kind == "offline":
        color = COLORS["offline"]
    return ft.Container(width=8, height=8, bgcolor=color, border_radius=8)


def mode_label(mode: str) -> str:
    return {
        "auto": "🤖 AUTO",
        "local_only": "🔒 SOMENTE LOCAL",
        "economy": "💰 ECONÔMICO",
        "manual": "🎛️ MANUAL",
    }.get(mode, mode)


def markdown_message(text: str, is_user: bool = False) -> ft.Markdown:
    return ft.Markdown(
        text,
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        code_theme="atom-one-dark",
    )
