"""Uživatelská nastavení perzistovaná jako JSON."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict

from .config import (
    APP_DATA_DIR, DEFAULT_LANGUAGE, DEFAULT_SAMPLE_RATE,
    REMOVE_SOUND_FILES, MAX_RECORDING_SECONDS, DEFAULT_TARGET_LANGUAGE,
)

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
    # Vlastní prompty pro korekci, klíč = kód jazyka nahrávky (např. "cs", "en").
    # Prázdný řetězec = použij defaultní prompt.
    custom_correction_prompts: Dict[str, str] = field(default_factory=dict)
    # Vlastní prompty pro překlad, klíč = kód cílového jazyka (např. "en", "de").
    custom_translation_prompts: Dict[str, str] = field(default_factory=dict)

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

    def get_correction_prompt(self, language: str) -> str:
        """Vrátí vlastní prompt pro korekci daného jazyka, nebo prázdný řetězec."""
        return self.custom_correction_prompts.get(language, "")

    def set_correction_prompt(self, language: str, prompt: str) -> None:
        if prompt.strip():
            self.custom_correction_prompts[language] = prompt.strip()
        else:
            self.custom_correction_prompts.pop(language, None)

    def get_translation_prompt(self, target_language: str) -> str:
        """Vrátí vlastní prompt pro překlad do daného jazyka, nebo prázdný řetězec."""
        return self.custom_translation_prompts.get(target_language, "")

    def set_translation_prompt(self, target_language: str, prompt: str) -> None:
        if prompt.strip():
            self.custom_translation_prompts[target_language] = prompt.strip()
        else:
            self.custom_translation_prompts.pop(target_language, None)


