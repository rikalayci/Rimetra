"""Ajan skill dosyası (SKILL.md) — Codex ve Claude Code için e-Nabız PDF giriş talimatları.

Tek kaynak depo kökündeki .agents/skills/rimetra-enabiz-import/SKILL.md dosyasıdır.
Docker imajında /app/agent/SKILL.md olarak kopyalanır.
"""
from __future__ import annotations

from pathlib import Path

SKILL_NAME = "rimetra-enabiz-import"
_CANDIDATES = [
    Path("/app/agent/SKILL.md"),
    Path(__file__).resolve().parents[2] / ".agents" / "skills" / SKILL_NAME / "SKILL.md",
]


def read_skill() -> str | None:
    for p in _CANDIDATES:
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None
