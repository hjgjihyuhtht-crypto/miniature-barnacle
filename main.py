"""NEXUS AI entrypoint for Flet run / APK packaging."""

from __future__ import annotations

import flet as ft

from app.main import main


if __name__ == "__main__":
    ft.run(main)
