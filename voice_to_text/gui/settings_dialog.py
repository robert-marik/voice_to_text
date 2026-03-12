"""Dialog s nastavením aplikace."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from ..config import LANGUAGES, TARGET_LANGUAGES
from ..settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nastavení")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._settings = settings
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Sestavení UI                                                         #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        # ── API klíč ────────────────────────────────────────────────────
        grp_api = QGroupBox("Groq API")
        api_form = QFormLayout(grp_api)
        api_form.setSpacing(10)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("gsk_... (nebo nastavte env GROQ_API_KEY)")
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setText(self._settings.groq_api_key)

        api_note = QLabel("Klíč je uložen lokálně v ~/.local/state/voice_to_text/settings.json")
        api_note.setStyleSheet("color: gray; font-size: 10px;")
        api_note.setWordWrap(True)

        api_form.addRow("API klíč:", self._api_key_edit)
        api_form.addRow("", api_note)
        root.addWidget(grp_api)

        # ── Přepis ──────────────────────────────────────────────────────
        grp_transcription = QGroupBox("Přepis")
        form = QFormLayout(grp_transcription)
        form.setSpacing(10)

        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        idx = self._lang_combo.findData(self._settings.language)
        self._lang_combo.setCurrentIndex(max(idx, 0))
        form.addRow("Jazyk nahrávky:", self._lang_combo)

        self._rate_combo = QComboBox()
        self._rate_combo.addItem("16 kHz (rychlejší)", 16000)
        self._rate_combo.addItem("44.1 kHz (věrnější)", 44100)
        idx = self._rate_combo.findData(self._settings.sample_rate)
        self._rate_combo.setCurrentIndex(max(idx, 0))
        form.addRow("Vzorkovací frekvence:", self._rate_combo)

        self._max_rec_spin = QSpinBox()
        self._max_rec_spin.setMinimum(10)
        self._max_rec_spin.setMaximum(600)
        self._max_rec_spin.setSingleStep(10)
        self._max_rec_spin.setSuffix(" s")
        self._max_rec_spin.setValue(self._settings.max_recording_seconds)
        form.addRow("Max. délka nahrávky:", self._max_rec_spin)

        root.addWidget(grp_transcription)

        # ── AI zpracování ────────────────────────────────────────────────
        grp_ai = QGroupBox("AI zpracování")
        ai_form = QFormLayout(grp_ai)
        ai_form.setSpacing(10)

        self._correction_cb = QCheckBox("Opravovat pravopis a čárky")
        self._correction_cb.setChecked(self._settings.use_correction)
        ai_form.addRow(self._correction_cb)

        self._translate_cb = QCheckBox("Překládat do jiného jazyka")
        self._translate_cb.setChecked(self._settings.translate_to_english)
        self._translate_cb.toggled.connect(self._on_translate_toggled)
        ai_form.addRow(self._translate_cb)

        self._target_lang_combo = QComboBox()
        for code, name in TARGET_LANGUAGES.items():
            self._target_lang_combo.addItem(name, code)
        idx = self._target_lang_combo.findData(self._settings.target_language)
        self._target_lang_combo.setCurrentIndex(max(idx, 0))
        self._target_lang_combo.setEnabled(self._settings.translate_to_english)
        ai_form.addRow("Cílový jazyk:", self._target_lang_combo)

        root.addWidget(grp_ai)

        # ── Tlačítka ─────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ #
    # Logika                                                               #
    # ------------------------------------------------------------------ #

    def _on_translate_toggled(self, checked: bool) -> None:
        self._target_lang_combo.setEnabled(checked)

    def _on_accept(self) -> None:
        self._settings.groq_api_key = self._api_key_edit.text().strip()
        self._settings.language = self._lang_combo.currentData()
        self._settings.sample_rate = self._rate_combo.currentData()
        self._settings.max_recording_seconds = self._max_rec_spin.value()
        self._settings.use_correction = self._correction_cb.isChecked()
        self._settings.translate_to_english = self._translate_cb.isChecked()
        self._settings.target_language = self._target_lang_combo.currentData()
        self._settings.save()
        self.accept()

