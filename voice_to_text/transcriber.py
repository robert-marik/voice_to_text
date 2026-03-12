"""Přepis audia, oprava pravopisu a překlad přes Groq API."""

import time

from groq import Groq

from .config import (
    WHISPER_MODEL, LLM_MODEL,
    TEMPERATURE_CORRECTION, TEMPERATURE_TRANSLATION, TEMPERATURE_TRANSCRIPTION,
    LANGUAGES, DEFAULT_CORRECTION_PROMPTS, DEFAULT_TRANSLATION_PROMPTS,
)
from .logger import Logger


def _get_default_correction_prompt(language: str) -> str:
    """Vrátí defaultní systémový prompt pro korekci podle jazyka nahrávky."""
    lang_name = LANGUAGES.get(language, language)
    if language in DEFAULT_CORRECTION_PROMPTS:
        return DEFAULT_CORRECTION_PROMPTS[language]
    return DEFAULT_CORRECTION_PROMPTS["default"].format(lang_name=lang_name)


def _get_default_translation_prompt(target_language: str) -> str:
    """Vrátí defaultní systémový prompt pro překlad podle cílového jazyka."""
    lang_name = LANGUAGES.get(target_language, target_language)
    template = DEFAULT_TRANSLATION_PROMPTS.get(
        target_language,
        DEFAULT_TRANSLATION_PROMPTS["default"],
    )
    return template.format(lang_name=lang_name)


class Transcriber:
    def __init__(self, logger: Logger, api_key: str = ""):
        self.logger = logger
        self._api_key = api_key
        self._client: Groq | None = None

    def _get_client(self) -> Groq:
        """Lazy inicializace klienta – umožňuje změnu API klíče za běhu."""
        if self._client is None or self._need_reinit:
            import os
            key = self._api_key or os.environ.get("GROQ_API_KEY", "")
            if not key:
                raise ValueError(
                    "GROQ_API_KEY není nastaven. Zadejte ho v Nastavení nebo jako env proměnnou."
                )
            self._client = Groq(api_key=key)
            self._need_reinit = False
        return self._client

    _need_reinit: bool = False

    def update_api_key(self, api_key: str) -> None:
        """Aktualizuje API klíč – příští volání použije nový klíč."""
        self._api_key = api_key
        self._client = None

    def transcribe(self, audio_path: str, language: str) -> str:
        """Přepíše audio soubor na text pomocí Whisper přes Groq."""
        start = time.time()
        client = self._get_client()
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(audio_path, f.read()),
                model=WHISPER_MODEL,
                language=language,
                response_format="text",
                temperature=TEMPERATURE_TRANSCRIPTION,
            )
        self.logger.log(f"Transkripce dokončena za {time.time() - start:.2f} sekund.")
        return transcription.strip()

    def correct(self, text: str, language: str, custom_prompt: str = "") -> str:
        """Opraví pravopis a čárky pomocí LLM.

        Pokud je předán custom_prompt, použije se místo defaultního.
        """
        try:
            self.logger.log("Provádím AI korekci textu...")
            system_prompt = custom_prompt.strip() if custom_prompt.strip() else _get_default_correction_prompt(language)
            if custom_prompt.strip():
                self.logger.log("Používám vlastní prompt pro korekci.")
            start = time.time()
            client = self._get_client()
            completion = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=TEMPERATURE_CORRECTION,
            )
            result = completion.choices[0].message.content.strip()
            self.logger.log(f"Korekce dokončena za {time.time() - start:.2f} sekund.")
            return result
        except Exception as e:
            self.logger.log(f"Chyba při korekci: {e}")
            return text

    def translate(self, text: str, target_language: str = "en", custom_prompt: str = "") -> str:
        """Přeloží text do zvoleného jazyka pomocí LLM.

        Pokud je předán custom_prompt, použije se místo defaultního.
        """
        try:
            lang_name = LANGUAGES.get(target_language, target_language)
            self.logger.log(f"Provádím překlad do {lang_name}...")
            system_prompt = custom_prompt.strip() if custom_prompt.strip() else _get_default_translation_prompt(target_language)
            if custom_prompt.strip():
                self.logger.log("Používám vlastní prompt pro překlad.")
            start = time.time()
            client = self._get_client()
            completion = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=TEMPERATURE_TRANSLATION,
            )
            result = completion.choices[0].message.content.strip()
            self.logger.log(f"Překlad dokončen za {time.time() - start:.2f} sekund.")
            return result
        except Exception as e:
            self.logger.log(f"Chyba při překladu: {e}")
            return text

