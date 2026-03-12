"""Hlavní okno aplikace s historií přepisů."""

from __future__ import annotations

import csv
import os
import subprocess
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPalette, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..history import TranscriptionEntry, TranscriptionHistory
from ..settings import Settings

if TYPE_CHECKING:
    pass


# ── Barvy stavového indikátoru ────────────────────────────────────────────
STATE_COLORS = {
    "idle":       "#4A90D9",   # modrá
    "recording":  "#E53935",   # červená
    "processing": "#F9A825",   # žlutá
}
STATE_LABELS = {
    "idle":       "Připraven  (2× Ctrl = nahrávání)",
    "recording":  "● Nahrávám…",
    "processing": "⏳ Zpracovávám…",
}


class StatusBar(QWidget):
    """Barevný pruh ve spodní části okna ukazující aktuální stav."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(20)
        self._label = QLabel(STATE_LABELS["idle"])
        self._label.setFont(QFont("Sans", 10))

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()

        self.set_state("idle")

    def set_state(self, state: str) -> None:
        color = STATE_COLORS.get(state, STATE_COLORS["idle"])
        label = STATE_LABELS.get(state, "")
        self._dot.setStyleSheet(f"color: {color}; font-size: 18px;")
        self._label.setText(label)
        self._label.setStyleSheet(f"color: {color}; font-weight: bold;" if state != "idle" else "")


class HistoryItem(QListWidgetItem):
    def __init__(self, entry: TranscriptionEntry):
        super().__init__()
        self.entry = entry
        preview = entry.final_text[:80].replace("\n", " ")
        if len(entry.final_text) > 80:
            preview += "…"
        self.setText(f"{entry.display_time}\n{preview}")
        self.setFont(QFont("Sans", 9))


class MainWindow(QMainWindow):
    # Signály pro thread-safe aktualizaci z jiných vláken
    state_changed = Signal(str)          # "idle" | "recording" | "processing"
    transcription_done = Signal(object)  # TranscriptionEntry

    def __init__(self, history: TranscriptionHistory, settings: Settings):
        super().__init__()
        self.history = history
        self.settings = settings

        self.setWindowTitle("Voice to Text")
        self.setMinimumSize(750, 520)
        self.resize(900, 600)

        self._build_ui()
        self._load_history()

        # Připojení signálů
        self.state_changed.connect(self._on_state_changed)
        self.transcription_done.connect(self._on_transcription_done)

    # ------------------------------------------------------------------ #
    # Sestavení UI                                                         #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # Toolbar
        toolbar = QToolBar("Akce")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 6px; padding: 4px; }")

        self._btn_settings = QPushButton("⚙  Nastavení")
        self._btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_settings.clicked.connect(self._open_settings)

        self._btn_export = QPushButton("💾  Exportovat historii")
        self._btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export.clicked.connect(self._export_history)

        self._btn_clear = QPushButton("🗑  Smazat historii")
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.clicked.connect(self._clear_history)

        toolbar.addWidget(self._btn_settings)
        toolbar.addWidget(self._btn_export)
        toolbar.addWidget(self._btn_clear)
        self.addToolBar(toolbar)

        # Splitter: seznam vlevo, detail vpravo
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Levý panel: seznam přepisů ────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        list_label = QLabel("Historie přepisů")
        list_label.setStyleSheet("font-weight: bold; padding: 6px 8px;")
        left_layout.addWidget(list_label)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSpacing(2)
        self._list.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self._list)

        # ── Pravý panel: detail ───────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(6)

        # Metadata řádek
        self._meta_label = QLabel("")
        self._meta_label.setStyleSheet("color: gray; font-size: 11px; padding: 4px 0;")
        right_layout.addWidget(self._meta_label)

        # Záložky: Původní / Opravený
        tabs_row = QHBoxLayout()
        self._btn_tab_corrected = QPushButton("Opravený text")
        self._btn_tab_raw = QPushButton("Původní přepis")
        for btn in (self._btn_tab_corrected, self._btn_tab_raw):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { border: none; padding: 4px 12px; border-bottom: 2px solid transparent; }"
                "QPushButton:checked { border-bottom: 2px solid #4A90D9; font-weight: bold; color: #4A90D9; }"
            )
            tabs_row.addWidget(btn)
        tabs_row.addStretch()
        self._btn_tab_corrected.setChecked(True)
        self._btn_tab_corrected.clicked.connect(lambda: self._switch_tab("corrected"))
        self._btn_tab_raw.clicked.connect(lambda: self._switch_tab("raw"))
        right_layout.addLayout(tabs_row)

        # Oddělovač
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ddd;")
        right_layout.addWidget(line)

        # Textový detail
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setFont(QFont("Sans", 11))
        self._detail.setStyleSheet("QTextEdit { border: none; padding: 8px; }")
        right_layout.addWidget(self._detail)

        # Tlačítko Kopírovat
        copy_row = QHBoxLayout()
        copy_row.addStretch()
        self._btn_copy = QPushButton("📋  Kopírovat")
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy.clicked.connect(self._copy_text)
        copy_row.addWidget(self._btn_copy)
        right_layout.addLayout(copy_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([280, 560])

        # Centrální widget
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(8, 8, 8, 0)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        # Stavový pruh
        self._status_bar = StatusBar()
        self.setStatusBar(None)
        central_layout.addWidget(self._status_bar)

        # Stav
        self._current_tab = "corrected"
        self._current_entry: TranscriptionEntry | None = None

    # ------------------------------------------------------------------ #
    # Logika                                                               #
    # ------------------------------------------------------------------ #

    def _load_history(self) -> None:
        self._list.clear()
        for entry in self.history.all():
            self._list.addItem(HistoryItem(entry))
        if self._list.count():
            self._list.setCurrentRow(0)

    def _on_item_selected(self, current: QListWidgetItem, _prev) -> None:
        if not isinstance(current, HistoryItem):
            self._detail.clear()
            self._meta_label.setText("")
            return
        entry = current.entry
        self._current_entry = entry
        lang_display = "cs 🇨🇿" if entry.language == "cs" else "en 🇬🇧"
        duration = f"{entry.duration_s:.1f}s" if entry.duration_s else "—"
        self._meta_label.setText(
            f"{entry.display_time}   ·   Jazyk: {lang_display}   ·   Délka nahrávky: {duration}"
        )
        self._refresh_detail()

    def _switch_tab(self, tab: str) -> None:
        self._current_tab = tab
        self._btn_tab_corrected.setChecked(tab == "corrected")
        self._btn_tab_raw.setChecked(tab == "raw")
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        if not self._current_entry:
            return
        if self._current_tab == "corrected":
            text = self._current_entry.corrected or self._current_entry.raw
        else:
            text = self._current_entry.raw
        self._detail.setPlainText(text)

    def _copy_text(self) -> None:
        text = self._detail.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Smazat historii",
            "Opravdu chcete smazat celou historii přepisů?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self._list.clear()
            self._detail.clear()
            self._meta_label.setText("")
            self._current_entry = None

    def _export_history(self) -> None:
        """Exportuje historii přepisů do CSV nebo TXT souboru."""
        entries = self.history.all()
        if not entries:
            QMessageBox.information(self, "Export", "Historie je prázdná – není co exportovat.")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportovat historii",
            os.path.expanduser("~/voice_to_text_history.csv"),
            "CSV soubor (*.csv);;Textový soubor (*.txt)",
        )
        if not path:
            return

        try:
            if path.endswith(".txt"):
                with open(path, "w", encoding="utf-8") as f:
                    for entry in entries:
                        f.write(f"=== {entry.display_time} | {entry.language} | {entry.duration_s:.1f}s ===\n")
                        f.write(entry.final_text)
                        f.write("\n\n")
            else:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Čas", "Jazyk", "Délka (s)", "Opravený text", "Původní přepis"])
                    for entry in entries:
                        writer.writerow([
                            entry.display_time,
                            entry.language,
                            entry.duration_s,
                            entry.corrected,
                            entry.raw,
                        ])
            QMessageBox.information(self, "Export", f"Historie exportována do:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Chyba exportu", str(e))

    def _open_settings(self) -> None:
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.settings, parent=self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    # Sloty pro signály z jiných vláken                                    #
    # ------------------------------------------------------------------ #

    @Slot(str)
    def _on_state_changed(self, state: str) -> None:
        self._status_bar.set_state(state)

    @Slot(object)
    def _on_transcription_done(self, entry: TranscriptionEntry) -> None:
        self.history.add(entry)
        item = HistoryItem(entry)
        self._list.insertItem(0, item)
        self._list.setCurrentItem(item)

    # ------------------------------------------------------------------ #
    # Zavření okna – schovat místo ukončit                                 #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        event.ignore()
        self.hide()

