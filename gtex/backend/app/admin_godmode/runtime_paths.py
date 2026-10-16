from __future__ import annotations

import os
from pathlib import Path

ADMIN_GODMODE_FILE = "admin_god_mode.json"
AUDIT_LOG_FILE = "admin_god_mode.audit.jsonl"
ADMIN_RUNTIME_DIR = ".runtime"


def admin_godmode_state_path(config_root: str | Path) -> Path:
    override = os.getenv("GTE_ADMIN_GODMODE_STATE_PATH")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path(config_root) / ADMIN_RUNTIME_DIR / ADMIN_GODMODE_FILE


def admin_godmode_audit_path(config_root: str | Path) -> Path:
    override = os.getenv("GTE_ADMIN_GODMODE_AUDIT_PATH")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path(config_root) / ADMIN_RUNTIME_DIR / AUDIT_LOG_FILE
