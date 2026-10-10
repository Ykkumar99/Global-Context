"""Configuration loading: config.yaml + .env + GCX_* environment overrides."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _coerce(raw: str, current: Any) -> Any:
    if isinstance(current, bool):
        return raw.lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    if isinstance(current, (list, dict)):
        return json.loads(raw)
    return raw


def _apply_env(cfg: dict, prefix: str = "GCX") -> None:
    for key, val in cfg.items():
        env_key = f"{prefix}_{key}".upper()
        if isinstance(val, dict):
            _apply_env(val, env_key)
        elif env_key in os.environ:
            cfg[key] = _coerce(os.environ[env_key], val)


class Config(dict):
    """dict with attribute access and path helpers."""

    __getattr__ = dict.get

    def path(self, key: str) -> Path:
        p = Path(self[key])
        return p if p.is_absolute() else ROOT / p

    @property
    def sarvam_key(self) -> str | None:
        return os.environ.get("SARVAM_API_KEY") or None

    @property
    def fallback_key(self) -> str | None:
        return os.environ.get("FALLBACK_LLM_API_KEY") or None

    @property
    def samvaad_key(self) -> str | None:
        return os.environ.get("SARVAM_SAMVAAD_API_KEY") or None


_CFG: Config | None = None


def load_config(path: str | os.PathLike | None = None) -> Config:
    global _CFG
    _load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    _apply_env(data)
    _CFG = Config(data)
    return _CFG


def get_config() -> Config:
    return _CFG or load_config()
