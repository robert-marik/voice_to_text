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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import LANGUAGES, TARGET_LANGUAGES
from ..transcriber import _get_default_correction_prompt, _get_default_translation_prompt
from ..settings import Settings


class PromptEditor(QGroupBox):
    """Widget pro editaci systémového promptu s tlačítkem pro zobrazení a zkopírování defaultu."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._default_prompt: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self._default_btn = QPushButton("Zobrazit výchozí prompt")
        self._default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._default_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self._default_btn.clicked.connect(self._toggle_default)
        top_row.addStretch()
        top_row.addWidget(self._default_btn)
        layout.addLayout(top_row)

        self._default_box = QTextEdit()
        self._default_box.setReadOnly(True)
        self._default_box.setVisible(False)
        self._default_box.setFixedHeight(100)
        self._default_box.setStyleSheet(
            "QTextEdit { background: #f5f5f5; color: #555; font-size: 10px; border: 1px solid #ddd; }"
        )
        layout.addWidget(self._default_box)

        copy_row = QHBoxLayout()
        self._copy_btn = QPushButton("📋 Zkopírovat výchozí do editoru")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self._copy_btn.setVisible(False)
        self._copy_btn.clicked.connect(self._copy_default_to_editor)
        copy_row.addStretch()
        copy_row.addWidget(self._copy_btn)
        layout.addLayout(copy_row)

        prompt_label = QLabel("Vlastní prompt (prázdné = použít výchozí):")
        prompt_label.setStyleSheet("font-size: 11px; color: #444;")
        layout.addWidget(prompt_label)

        self._editor = QTextEdit()
        self._editor.setFixedHeight(100)
        self._editor.setPlaceholderText("Nechte prázdné pro použití výchozího promptu…")
        self._editor.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._editor)

        reset_row = QHBoxLayout()
        self._reset_btn = QPushButton("✕ Smazat vlastní prompt")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet("font-size: 11px; padding: 2px 8px; color: #c00;")
        self._reset_btn.clicked.connect(lambda: self._editor.clear())
        reset_row.addStretch()
        reset_row.addWidget(self._reset_btn)
        layout.addLayout(reset_row)

    def _toggle_default(self) -> None:
        visible = self._default_box.isVisible()
        self._default_box.setVisible(not visible)
        self._copy_btn.setVisible(not visible)
        self._default_btn.setText(
            "Skrýt výchozí prompt" if not visible else "Zobrazit výchozí prompt"
        )

    def _copy_default_to_editor(self) -> None:
        self._editor.setPlainText(self._default_prompt)

    def set_default_prompt(self, prompt: str) -> None:
        self._default_prompt = prompt
        self._default_box.setPlainText(prompt)

    def set_custom_prompt(self, prompt: str) -> None:
        self._editor.setPlainText(prompt)

    def get_custom_prompt(self) -> str:
        return self._editor.toPlainText().strip()


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nastavení")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        self.setModal(True)
        self._settings = settings
        self._build_ui()
        self._refresh_prompt_editors()

    # ------------------------------------------------------------------ #
    # Sestavení UI                                                         #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        tabs = QTabWidget()
        tabs.addTab(self._build_tab_general(), "🎙  Přepis")
        tabs.addTab(self._build_tab_ai(), "🤖  AI zpracování")
        tabs.addTab(self._build_tab_prompts(), "📝  Prompty")
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_tab_general(self) -> QWidget:
        """Tab: Přepis – API klíč, jazyk, vzorkovací frekvence, max délka."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # API klíč
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
        layout.addWidget(grp_api)

        # Nahrávání
        grp_rec = QGroupBox("Nahrávání")
        rec_form = QFormLayout(grp_rec)
        rec_form.setSpacing(10)

        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        idx = self._lang_combo.findData(self._settings.language)
        self._lang_combo.setCurrentIndex(max(idx, 0))
        self._lang_combo.currentIndexChanged.connect(self._refresh_prompt_editors)
        rec_form.addRow("Jazyk nahrávky:", self._lang_combo)

        self._rate_combo = QComboBox()
        self._rate_combo.addItem("16 kHz (rychlejší)", 16000)
        self._rate_combo.addItem("44.1 kHz (věrnější)", 44100)
        idx = self._rate_combo.findData(self._settings.sample_rate)
        self._rate_combo.setCurrentIndex(max(idx, 0))
        rec_form.addRow("Vzorkovací frekvence:", self._rate_combo)

        self._max_rec_spin = QSpinBox()
        self._max_rec_spin.setMinimum(10)
        self._max_rec_spin.setMaximum(600)
        self._max_rec_spin.setSingleStep(10)
        self._max_rec_spin.setSuffix(" s")
        self._max_rec_spin.setValue(self._settings.max_recording_seconds)
        rec_form.addRow("Max. délka nahrávky:", self._max_rec_spin)

        layout.addWidget(grp_rec)
        layout.addStretch()
        return tab

    def _build_tab_ai(self) -> QWidget:
        """Tab: AI zpracování – korekce, překlad, cílový jazyk."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        grp_ai = QGroupBox("AI zpracování")
        ai_form = QFormLayout(grp_ai)
        ai_form.setSpacing(12)

        self._correction_cb = QCheckBox("Opravovat pravopis a čárky")
        self._correction_cb.setChecked(self._settings.use_correction)
        self._correction_cb.toggled.connect(self._refresh_prompt_editors)
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
        self._target_lang_combo.currentIndexChanged.connect(self._refresh_prompt_editors)
        ai_form.addRow("Cílový jazyk:", self._target_lang_combo)

        layout.addWidget(grp_ai)
        layout.addStretch()
        return tab

    def _build_tab_prompts(self) -> QWidget:
        """Tab: Prompty – vlastní systémové prompty pro korekci a překlad."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "Vlastní prompt přepíše výchozí instrukci pro AI. "
            "Ponechte prázdné pro použití výchozího nastavení."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(info)

        self._prompt_correction = PromptEditor("Prompt pro korekci")
        layout.addWidget(self._prompt_correction)

        self._prompt_translation = PromptEditor("Prompt pro překlad")
        layout.addWidget(self._prompt_translation)

        layout.addStretch()
        return tab

    # ------------------------------------------------------------------ #
    # Logika                                                               #
    # ------------------------------------------------------------------ #

    def _on_translate_toggled(self, checked: bool) -> None:
        self._target_lang_combo.setEnabled(checked)
        self._refresh_prompt_editors()

    def _refresh_prompt_editors(self) -> None:
        """Aktualizuje defaultní prompty a viditelnost editorů podle aktuálního výběru."""
        lang = self._lang_combo.currentData() or self._settings.language
        target = self._target_lang_combo.currentData() or self._settings.target_language

        correction_active = self._correction_cb.isChecked()
        self._prompt_correction.setVisible(correction_active)
        if correction_active:
            self._prompt_correction.set_default_prompt(_get_default_correction_prompt(lang))
            self._prompt_correction.set_custom_prompt(
                self._settings.get_correction_prompt(lang)
            )

        translation_active = self._translate_cb.isChecked()
        self._prompt_translation.setVisible(translation_active)
        if translation_active:
            self._prompt_translation.set_default_prompt(_get_default_translation_prompt(target))
            self._prompt_translation.set_custom_prompt(
                self._settings.get_translation_prompt(target)
            )

    def _on_accept(self) -> None:
        lang = self._lang_combo.currentData()
        target = self._target_lang_combo.currentData()

        self._settings.groq_api_key = self._api_key_edit.text().strip()
        self._settings.language = lang
        self._settings.sample_rate = self._rate_combo.currentData()
        self._settings.max_recording_seconds = self._max_rec_spin.value()
        self._settings.use_correction = self._correction_cb.isChecked()
        self._settings.translate_to_english = self._translate_cb.isChecked()
        self._settings.target_language = target

        if self._correction_cb.isChecked():
            self._settings.set_correction_prompt(lang, self._prompt_correction.get_custom_prompt())
        if self._translate_cb.isChecked():
            self._settings.set_translation_prompt(target, self._prompt_translation.get_custom_prompt())

        self._settings.save()
        self.accept()


from ..config import LANGUAGES, TARGET_LANGUAGES
from ..transcriber import _get_default_correction_prompt, _get_default_translation_prompt
from ..settings import Settings

