"""Uživatelská nastavení perzistovaná jako JSON."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from .config import APP_DATA_DIR, DEFAULT_LANGUAGE, DEFAULT_SAMPLE_RATE, REMOVE_SOUND_FILES, MAX_RECORDING_SECONDS, DEFAULT_TARGET_LANGUAGE

SETTINGS_PATH = os.path.join(APP_DATA_DIR, "settings.json")


@dataclass
class Settings:
    language: str = DEFAULT_LANGUAGE
    sample_rate: int = DEFAULT_SAMPLE_RATE
    use_correction: bool = True
    translate_to_english: bool = False
    target_language: str = DEFAULT_TARGET_LANGUAGE
    remove_sound_files: bool = REMOVE_SOUND_FILES
    groq_api_key: str = ""
    max_recording_seconds: int = MAX_RECORDING_SECONDS

    # ------------------------------------------------------------------ #

    def save(self, path: str = SETTINGS_PATH) -> None:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str = SETTINGS_PATH) -> "Settings":
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()

    def effective_api_key(self) -> str:
        """Vrátí API klíč – z nastavení nebo z env proměnné."""
        return self.groq_api_key or os.environ.get("GROQ_API_KEY", "")

