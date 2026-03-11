"""Systray ikona, keyboard listener a orchestrace nahrávání (PySide6)."""

from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from pynput import keyboard as kb

from .audio import AudioRecorder
from .clipboard import ClipboardPaster
from .config import APP_DATA_DIR, MAX_RECORDING_SECONDS, TEMPERATURE_CORRECTION, TEMPERATURE_TRANSLATION, TEMPERATURE_TRANSCRIPTION
from .history import TranscriptionEntry, TranscriptionHistory
from .logger import Logger
from .music import MusicController
from .settings import Settings
from .transcriber import Transcriber


def _make_icon(color: str, size: int = 22) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()
    return QIcon(px)


class AppController(QObject):
    """Propojuje systray, klávesnici, nahrávání a hlavní okno."""

    _state_sig = Signal(str)

    def __init__(self, app: QApplication):
        super().__init__()
        os.makedirs(APP_DATA_DIR, exist_ok=True)

        # QPixmap lze vytvořit až po QApplication – ikony inicializujeme zde
        self._icons = {
            "idle":       _make_icon("#4A90D9"),
            "recording":  _make_icon("#E53935"),
            "processing": _make_icon("#F9A825"),
        }

        self.app = app
        self.settings = Settings.load()
        self.history = TranscriptionHistory()
        self.logger = Logger()
        self.music = MusicController(self.logger)
        self.paster = ClipboardPaster(self.logger)
        self.transcriber = Transcriber(self.logger)

        self.recording = False
        self.was_playing = False
        self._last_ctrl = 0.0
        self._recorder: AudioRecorder | None = None

        self._tray = QSystemTrayIcon(self._icons["idle"], self.app)
        self._tray.setToolTip("Voice to Text  (2x Ctrl = nahravani)")
        self._tray.activated.connect(self._on_tray_activated)
        self._build_tray_menu()
        self._tray.show()

        from .gui.main_window import MainWindow
        self._window = MainWindow(self.history, self.settings)
        self._state_sig.connect(self._window.state_changed)

        self._listener = kb.Listener(on_press=self._on_key_press)
        self._listener.daemon = True
        self._listener.start()

        self.logger.log("Aplikace spustena. Stiskni 2x Ctrl pro start/stop nahravani.")
        self.logger.log(f"Max delka nahravani je nastavena na {MAX_RECORDING_SECONDS} sekund.")
        self.logger.log(f"Teplota pro transkripci je nastavena na {TEMPERATURE_TRANSCRIPTION}.")
        self.logger.log(f"Teplota pro korekci je nastavena na {TEMPERATURE_CORRECTION}.")
        self.logger.log(f"Teplota pro preklad je nastavena na {TEMPERATURE_TRANSLATION}.")

    # ── Tray menu ──────────────────────────────────────────────────────

    def _build_tray_menu(self) -> None:
        menu = QMenu()
        menu.addAction("Zobrazit historii", self._show_window)
        menu.addAction("Nastaveni", self._open_settings)
        menu.addSeparator()
        menu.addAction("Otevrit log", self.logger.open_log_file)
        menu.addSeparator()
        menu.addAction("Ukoncit", self._quit)
        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _open_settings(self) -> None:
        from .gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.settings, parent=self._window)
        dialog.exec()

    def _quit(self) -> None:
        self.logger.log("Ukoncovani aplikace...")
        self._listener.stop()
        self.app.quit()

    # ── Stav ikony ─────────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        self._tray.setIcon(self._icons.get(state, self._icons["idle"]))
        self._state_sig.emit(state)

    # ── Klavesnice ─────────────────────────────────────────────────────

    def _on_key_press(self, key) -> None:
        if key not in (kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r):
            return
        now = time.time()
        if now - self._last_ctrl < 0.4:
            if not self.recording:
                self._start_recording()
            else:
                self._stop_recording()
        self._last_ctrl = now

    # ── Nahravani ──────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        self.recording = True
        self._set_state("recording")
        self.was_playing = self.music.pause_if_playing()
        threading.Thread(target=self._record_and_process, daemon=True).start()

    def _stop_recording(self) -> None:
        self.recording = False
        if self.was_playing:
            self.music.resume()

    def _record_and_process(self) -> None:
        text_to_paste = ""
        raw_text = ""
        start_ts = time.time()
        recorder = AudioRecorder(self.logger, self.settings.sample_rate)
        self._recorder = recorder
        try:
            recorder.start()
            recorder.wait_for_stop(
                stop_flag_fn=lambda: self.recording,
                on_timeout_fn=self._stop_recording,
            )
            recorder.stop()
            self._set_state("processing")

            if not recorder.normalize():
                self.logger.log("Normalizace selhala, preskakuji prepis.")
                return

            raw_text = self.transcriber.transcribe(
                recorder.normalized_path, self.settings.language
            )
            self.logger.log(f"Puvodni prepis: {raw_text}")

            if raw_text:
                text_to_paste = raw_text
                if self.settings.use_correction:
                    text_to_paste = self.transcriber.correct(raw_text, self.settings.language)
                if self.settings.translate_to_english:
                    text_to_paste = self.transcriber.translate(text_to_paste)
                self.paster.paste(text_to_paste)

        except Exception as e:
            self.logger.log(f"CHYBA v procesu nahravani: {e}")
        finally:
            duration = time.time() - start_ts
            entry = TranscriptionEntry(
                timestamp=start_ts,
                raw=raw_text,
                corrected=text_to_paste,
                language=self.settings.language,
                duration_s=round(duration, 1),
            )
            self._window.transcription_done.emit(entry)
            self._set_state("idle")
            if self.settings.remove_sound_files:
                for path in (self._recorder.audio_path, self._recorder.normalized_path):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        pass
            self._recorder = None
