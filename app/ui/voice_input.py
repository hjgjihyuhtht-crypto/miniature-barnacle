"""Voice input overlay / dialog."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from app.ui.components import COLORS


class VoiceInputPanel(ft.Container):
    def __init__(
        self,
        on_send: Callable[[str], None],
        on_cancel: Callable[[], None],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.on_send = on_send
        self.on_cancel = on_cancel
        self.on_start = on_start
        self.on_stop = on_stop
        self.state = ft.Text("Pronto para gravar", color=COLORS["muted"])
        self.timer = ft.Text("00:00", size=28, weight=ft.FontWeight.BOLD, color=COLORS["text"])
        self.transcript = ft.TextField(
            multiline=True,
            min_lines=3,
            max_lines=6,
            visible=False,
            border_color=COLORS["accent2"],
            color=COLORS["text"],
        )
        self.btn_start = ft.ElevatedButton("Gravar", icon=ft.Icons.MIC, on_click=lambda e: self._start())
        self.btn_stop = ft.ElevatedButton(
            "Parar", icon=ft.Icons.STOP, bgcolor=COLORS["danger"], visible=False, on_click=lambda e: self._stop()
        )
        self.btn_send = ft.ElevatedButton("Enviar", visible=False, on_click=lambda e: self._send())
        self.btn_edit = ft.TextButton("Editar", visible=False, on_click=lambda e: None)
        self.btn_cancel = ft.TextButton("Cancelar", on_click=lambda e: self.on_cancel())
        super().__init__(
            visible=False,
            bgcolor=COLORS["panel"],
            padding=16,
            border_radius=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("🔴 Gravando..." if False else "🎤 Voz", color=COLORS["text"], size=16, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    self.state,
                    self.timer,
                    self.transcript,
                    ft.Row([self.btn_start, self.btn_stop, self.btn_send, self.btn_edit, self.btn_cancel]),
                ],
                tight=True,
                spacing=10,
            ),
        )

    def open(self) -> None:
        self.visible = True
        self.state.value = "Toque em Gravar"
        self.transcript.visible = False
        self.btn_send.visible = False
        self.btn_stop.visible = False
        self.btn_start.visible = True
        self.update()

    def _start(self) -> None:
        self.state.value = "🔴 Gravando..."
        self.btn_start.visible = False
        self.btn_stop.visible = True
        self.update()
        self.on_start()

    def _stop(self) -> None:
        self.state.value = "Transcrevendo..."
        self.btn_stop.visible = False
        self.update()
        self.on_stop()

    def show_transcript(self, text: str) -> None:
        self.state.value = "🎤 Transcrição:"
        self.transcript.value = text
        self.transcript.visible = True
        self.btn_send.visible = True
        self.btn_edit.visible = True
        self.update()

    def set_timer(self, seconds: float) -> None:
        m = int(seconds) // 60
        s = int(seconds) % 60
        self.timer.value = f"{m:02d}:{s:02d}"
        self.update()

    def _send(self) -> None:
        self.on_send(self.transcript.value or "")
        self.visible = False
        self.update()
