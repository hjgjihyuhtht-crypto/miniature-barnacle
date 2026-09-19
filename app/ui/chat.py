"""Main chat UI."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional

import flet as ft

from app.database.db import LocalDB
from app.database.models import AppSettings
from app.services.api_client import NexusAPIClient
from app.services.attachments import basename, is_allowed
from app.services.streaming import stream_chat
from app.services.voice import VoiceRecorder
from app.ui.components import COLORS, indicator_dot, markdown_message, mode_label
from app.ui.model_selector import ModelSelector
from app.ui.voice_input import VoiceInputPanel


class ChatView(ft.Column):
    def __init__(self, page: ft.Page, db: LocalDB, settings: AppSettings):
        self.page = page
        self.db = db
        self.settings = settings
        self.conversation_id: Optional[str] = None
        self.attachment_ids: list[str] = []
        self.pending_file: Optional[str] = None
        self.generating = False
        self.cancel_stream = False
        self.recorder = VoiceRecorder()
        self._timer_task: Optional[asyncio.Task] = None

        self.messages = ft.ListView(expand=True, spacing=12, auto_scroll=True, padding=16)
        self.input = ft.TextField(
            hint_text="Digite uma mensagem...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=5,
            border_color=COLORS["accent2"],
            color=COLORS["text"],
            on_submit=lambda e: self.page.run_task(self.send),
        )
        self.memory_chip = ft.Text("🧠 Memória ativa", color=COLORS["accent"], size=12)
        self.status = ft.Text("", color=COLORS["muted"], size=12)
        self.attach_label = ft.Text("", color=COLORS["muted"], size=12)
        self.selector = ModelSelector(self._on_mode_model)
        self.voice_panel = VoiceInputPanel(
            on_send=lambda t: self.page.run_task(self._send_text, t),
            on_cancel=self._close_voice,
            on_start=self._start_recording,
            on_stop=lambda: self.page.run_task(self._stop_and_transcribe),
        )
        self.file_picker = ft.FilePicker(on_result=self._on_file)
        self.page.overlay.append(self.file_picker)

        composer = ft.Container(
            bgcolor=COLORS["panel"],
            padding=10,
            border_radius=12,
            content=ft.Column(
                [
                    self.attach_label,
                    self.voice_panel,
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.ATTACH_FILE,
                                tooltip="Anexo",
                                on_click=lambda e: self.file_picker.pick_files(
                                    allow_multiple=False,
                                    allowed_extensions=["txt", "pdf", "docx", "png", "jpg", "jpeg", "webp"],
                                ),
                            ),
                            self.input,
                            ft.IconButton(
                                ft.Icons.MIC,
                                tooltip="Voz",
                                icon_color=COLORS["accent"],
                                on_click=lambda e: self._open_voice(),
                            ),
                            ft.IconButton(
                                ft.Icons.SEND,
                                tooltip="Enviar",
                                icon_color=COLORS["accent"],
                                on_click=lambda e: self.page.run_task(self.send),
                            ),
                            ft.IconButton(
                                ft.Icons.STOP,
                                tooltip="Parar",
                                icon_color=COLORS["danger"],
                                on_click=lambda e: self._stop_generation(),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ]
            ),
        )

        super().__init__(
            expand=True,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    content=ft.Row(
                        [
                            ft.Text("NEXUS AI", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                            ft.Container(expand=True),
                            self.selector,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(padding=ft.padding.symmetric(horizontal=16), content=ft.Row([self.memory_chip, self.status])),
                self.messages,
                composer,
            ],
            spacing=0,
        )

    def client(self) -> NexusAPIClient:
        return NexusAPIClient(self.settings.server_url, self.settings.api_key)

    def _on_mode_model(self, mode: str, model: str) -> None:
        self.settings.routing_mode = mode
        self.settings.selected_model = model
        self.db.set_setting("routing_mode", mode)
        self.db.set_setting("selected_model", model)

    def new_conversation(self) -> None:
        self.conversation_id = str(uuid.uuid4())
        self.messages.controls.clear()
        self.attachment_ids.clear()
        self.attach_label.value = ""
        self.db.upsert_conversation(
            {
                "id": self.conversation_id,
                "title": "Nova conversa",
                "model": self.settings.selected_model,
                "routing_mode": self.settings.routing_mode,
            }
        )
        self.update()

    def load_conversation(self, cid: str) -> None:
        self.conversation_id = cid
        self.messages.controls.clear()
        for m in self.db.list_messages(cid):
            self._append_bubble(m["role"], m["content"], m.get("model"), m.get("meta") or {})
        self.update()

    def _append_bubble(
        self,
        role: str,
        content: str,
        model: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> ft.Container:
        meta = meta or {}
        header_controls = []
        if role == "assistant":
            router = meta.get("router") or {}
            if router:
                loc = router.get("location", "api")
                kind = "local" if loc == "vps" else "api"
                header_controls = [
                    ft.Text("🤖 NEXUS AUTO" if router.get("mode") == "auto" else "NEXUS", color=COLORS["accent"]),
                    ft.Text(f"Usando: {router.get('display_name', model)}", color=COLORS["text"]),
                    ft.Row(
                        [
                            indicator_dot(kind),
                            ft.Text(
                                "Local • VPS" if kind == "local" else "API",
                                color=COLORS["muted"],
                                size=12,
                            ),
                        ],
                        spacing=6,
                    ),
                ]
                if router.get("reason"):
                    header_controls.append(
                        ft.Text(f"Motivo: {router['reason']}", color=COLORS["muted"], size=12)
                    )
            memories = meta.get("memories_used") or []
            if memories:
                header_controls.append(
                    ft.TextButton(
                        f"🧠 {len(memories)} memórias utilizadas",
                        on_click=lambda e, mems=memories: self._show_memories(mems),
                    )
                )
        else:
            header_controls = [ft.Text("Você", color=COLORS["accent2"], weight=ft.FontWeight.BOLD)]

        bubble = ft.Container(
            bgcolor=COLORS["panel"] if role == "assistant" else "#18233A",
            padding=12,
            border_radius=10,
            content=ft.Column(
                header_controls + [markdown_message(content, is_user=(role == "user"))],
                spacing=6,
                tight=True,
            ),
        )
        self.messages.controls.append(bubble)
        return bubble

    def _show_memories(self, memories: list[dict]) -> None:
        lines = "\n".join(f"• {m.get('content')}" for m in memories)
        self.page.open(
            ft.AlertDialog(
                title=ft.Text("Memórias utilizadas"),
                content=ft.Text(lines),
                actions=[ft.TextButton("OK", on_click=lambda e: self.page.close(e.control.parent))],
            )
        )

    def _open_voice(self) -> None:
        self.voice_panel.open()
        self.update()

    def _close_voice(self) -> None:
        self.voice_panel.visible = False
        self.update()

    def _start_recording(self) -> None:
        self.recorder.start()
        if self._timer_task:
            self._timer_task.cancel()
        self._timer_task = self.page.run_task(self._tick_timer)

    async def _tick_timer(self) -> None:
        while self.recorder.recording:
            self.voice_panel.set_timer(self.recorder.elapsed())
            await asyncio.sleep(0.5)

    async def _stop_and_transcribe(self) -> None:
        path = self.recorder.stop()
        if not path:
            return
        try:
            result = await self.client().transcribe(path)
            self.voice_panel.show_transcript(result.get("text", ""))
        except Exception as exc:
            self.voice_panel.state.value = f"Erro: {exc}"
            self.voice_panel.update()

    def _on_file(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        path = e.files[0].path
        if not path or not is_allowed(path):
            self.status.value = "Tipo de arquivo não suportado"
            self.update()
            return
        self.pending_file = path
        self.attach_label.value = f"📎 {basename(path)}"
        self.update()
        self.page.run_task(self._upload_pending)

    async def _upload_pending(self) -> None:
        if not self.pending_file:
            return
        try:
            res = await self.client().upload_attachment(self.pending_file, self.conversation_id)
            self.attachment_ids.append(res["id"])
            self.status.value = "Anexo pronto"
        except Exception as exc:
            self.status.value = f"Falha no anexo: {exc}"
        self.update()

    def _stop_generation(self) -> None:
        self.cancel_stream = True

    async def send(self) -> None:
        text = (self.input.value or "").strip()
        if not text:
            return
        self.input.value = ""
        self.update()
        await self._send_text(text)

    async def _send_text(self, text: str) -> None:
        if not self.conversation_id:
            self.new_conversation()
        self._append_bubble("user", text)
        self.db.add_message(self.conversation_id, "user", text)
        self.db.upsert_conversation(
            {
                "id": self.conversation_id,
                "title": text[:60],
                "model": self.settings.selected_model,
                "routing_mode": self.settings.routing_mode,
            }
        )
        self.update()

        assistant_box = self._append_bubble("assistant", "…")
        content_holder = {"text": ""}
        router_meta: dict[str, Any] = {}

        def on_router(data: dict) -> None:
            nonlocal router_meta
            router_meta = data
            if data.get("conversation_id"):
                self.conversation_id = data["conversation_id"]

        def on_token(token: str) -> None:
            content_holder["text"] += token
            # rebuild last bubble content
            self.messages.controls[-1] = self._make_assistant_live(content_holder["text"], router_meta)
            self.messages.update()

        payload = {
            "model": self.settings.selected_model if self.settings.routing_mode == "manual" else "auto",
            "messages": [{"role": "user", "content": text}],
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": True,
            "conversation_id": self.conversation_id,
            "routing_mode": self.settings.routing_mode,
            "memory_enabled": self.settings.memory_enabled,
            "allow_external_apis": self.settings.allow_external_apis,
            "attachment_ids": list(self.attachment_ids),
        }
        self.attachment_ids.clear()
        self.attach_label.value = ""
        self.generating = True
        self.cancel_stream = False
        try:
            full = await stream_chat(self.client(), payload, on_router=on_router, on_token=on_token)
            if self.cancel_stream:
                full = content_holder["text"] + "\n\n[geração interrompida]"
            self.messages.controls[-1] = self._make_assistant_live(full or content_holder["text"], router_meta)
            self.db.add_message(
                self.conversation_id,
                "assistant",
                full or content_holder["text"],
                model=router_meta.get("selected_model"),
                meta={"router": router_meta, "memories_used": router_meta.get("memories_used") or []},
            )
            suggestions = router_meta.get("memory_suggestions") or []
            if suggestions and self.settings.ask_before_save:
                await self._ask_remember(suggestions[0])
        except Exception as exc:
            detail = str(exc)
            self.messages.controls[-1] = ft.Container(
                bgcolor=COLORS["panel"],
                padding=12,
                border_radius=10,
                content=ft.Column(
                    [
                        ft.Text(detail, color=COLORS["danger"]),
                        ft.Row(
                            [
                                ft.ElevatedButton("Tentar novamente", on_click=lambda e: self.page.run_task(self._send_text, text)),
                                ft.TextButton("Usar Qwen", on_click=lambda e: self._force_model("qwen-local", text)),
                                ft.TextButton("Usar Llama", on_click=lambda e: self._force_model("llama-local", text)),
                                ft.TextButton("Usar OpenAI", on_click=lambda e: self._force_model("openai:gpt-4o-mini", text)),
                                ft.TextButton("Usar Gemini", on_click=lambda e: self._force_model("gemini:gemini-2.0-flash", text)),
                                ft.TextButton("Usar Claude", on_click=lambda e: self._force_model("claude:claude-sonnet-4-20250514", text)),
                            ],
                            wrap=True,
                        ),
                    ]
                ),
            )
        finally:
            self.generating = False
            self.update()

    def _force_model(self, model: str, text: str) -> None:
        self.settings.routing_mode = "manual"
        self.settings.selected_model = model
        self.selector.mode_dd.value = "manual"
        self.selector.model_dd.visible = True
        self.selector.model_dd.value = model
        self.page.run_task(self._send_text, text)

    def _make_assistant_live(self, text: str, router: dict) -> ft.Container:
        kind = "local" if router.get("location") == "vps" else "api"
        controls = []
        if router:
            controls.extend(
                [
                    ft.Text("🤖 NEXUS AUTO" if router.get("mode") == "auto" else "NEXUS", color=COLORS["accent"]),
                    ft.Text(f"Usando: {router.get('display_name', '')}", color=COLORS["text"]),
                    ft.Row(
                        [
                            indicator_dot(kind if router.get("status") != "offline" else "offline"),
                            ft.Text("Local • VPS" if kind == "local" else "API", color=COLORS["muted"], size=12),
                        ]
                    ),
                    ft.Text(f"Motivo: {router.get('reason', '')}", color=COLORS["muted"], size=12),
                ]
            )
            mems = router.get("memories_used") or []
            if mems:
                controls.append(ft.Text(f"🧠 {len(mems)} memórias utilizadas", color=COLORS["accent"], size=12))
        controls.append(markdown_message(text))
        return ft.Container(
            bgcolor=COLORS["panel"],
            padding=12,
            border_radius=10,
            content=ft.Column(controls, spacing=6, tight=True),
        )

    async def _ask_remember(self, suggestion: dict) -> None:
        async def remember(e):
            try:
                await self.client().create_memory(
                    {
                        "type": suggestion.get("type", "preference"),
                        "content": suggestion.get("content", ""),
                        "source": "user_confirm",
                        "importance": 0.7,
                    }
                )
                self.status.value = "Memória salva"
            except Exception as exc:
                self.status.value = f"Falha ao salvar memória: {exc}"
            self.page.close(dialog)
            self.update()

        dialog = ft.AlertDialog(
            title=ft.Text("🧠 Lembrar disso?"),
            content=ft.Text(suggestion.get("content", "")),
            actions=[
                ft.TextButton("Lembrar", on_click=remember),
                ft.TextButton("Não lembrar", on_click=lambda e: self.page.close(dialog)),
            ],
        )
        self.page.open(dialog)

    async def refresh_models(self) -> None:
        try:
            models = await self.client().list_models()
            self.selector.set_models(models)
            self.memory_chip.value = "🧠 Memória ativa" if self.settings.memory_enabled else "🧠 Memória off"
        except Exception as exc:
            self.status.value = f"Servidor: {exc}"
        self.update()
