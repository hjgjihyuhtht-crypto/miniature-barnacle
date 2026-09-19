#!/usr/bin/env python3
"""NEXUS debug probe — dependency / import / backend boot status."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

LOG = Path("/root/.cursor/debug-ab7b57.log")
SESSION = "ab7b57"


def log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION,
        "runId": "dep-probe",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # #endregion


def main() -> int:
    log("A", "probe.py:platform", "python platform", {
        "version": sys.version,
        "platform": sys.platform,
        "executable": sys.executable,
    })

    mods = [
        ("pydantic", "A"),
        ("pydantic_core", "A"),
        ("fastapi", "B"),
        ("uvicorn", "B"),
        ("aiosqlite", "B"),
        ("httpx", "B"),
        ("pytest", "C"),
    ]
    for name, hid in mods:
        try:
            m = __import__(name)
            log(hid, f"probe.py:import:{name}", "import ok", {
                "module": name,
                "version": getattr(m, "__version__", None),
            })
        except Exception as exc:
            log(hid, f"probe.py:import:{name}", "import fail", {
                "module": name,
                "error": type(exc).__name__,
                "detail": str(exc)[:300],
            })

    # Backend import (H-D)
    try:
        sys.path.insert(0, "/root/nexus-ai")
        from backend.config import get_settings  # noqa: WPS433

        get_settings.cache_clear()
        s = get_settings()
        log("D", "probe.py:backend.config", "config ok", {
            "db_path": str(s.db_path),
            "local_runtime": s.local_runtime,
        })
    except Exception as exc:
        log("D", "probe.py:backend.config", "config fail", {
            "error": type(exc).__name__,
            "detail": str(exc)[:400],
        })

    try:
        from backend.main import create_app  # noqa: WPS433

        app = create_app()
        routes = [getattr(r, "path", None) for r in app.routes][:20]
        log("E", "probe.py:backend.main", "create_app ok", {"routes": routes})
    except Exception as exc:
        log("E", "probe.py:backend.main", "create_app fail", {
            "error": type(exc).__name__,
            "detail": str(exc)[:400],
        })

    print(f"Wrote debug logs to {LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
