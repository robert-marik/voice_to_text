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
from .config import APP_DATA_DIR
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
    _notify_sig = Signal(str, str)   # title, message – pro tray notifikace z vláken

    def __init__(self, app: QApplication):
        super().__init__()
        os.makedirs(APP_DATA_DIR, exist_ok=True)

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
        self.transcriber = Transcriber(self.logger, self.settings.effective_api_key())

        self.recording = False
        self.was_playing = False
        self._lock = threading.Lock()   # ochrana sdíleného stavu
        self._last_ctrl: float = 0.0
        self._recorder: AudioRecorder | None = None

        self._tray = QSystemTrayIcon(self._icons["idle"], self.app)
        self._tray.setToolTip("Voice to Text  (2x Ctrl = nahrávání)")
        self._tray.activated.connect(self._on_tray_activated)
        self._build_tray_menu()
        self._tray.show()

        from .gui.main_window import MainWindow
        self._window = MainWindow(self.history, self.settings)
        self._state_sig.connect(self._window.state_changed)
        self._notify_sig.connect(self._show_notification)

        self._listener = kb.Listener(on_press=self._on_key_press)
        self._listener.daemon = True
        self._listener.start()

        self.logger.log("Aplikace spustena. Stiskni 2x Ctrl pro start/stop nahravani.")
        self.logger.log(f"Max delka nahravani: {self.settings.max_recording_seconds}s.")

        # Upozornit uživatele, pokud chybí API klíč
        if not self.settings.effective_api_key():
            self._show_notification(
                "Voice to Text – chybí API klíč",
                "Zadejte GROQ_API_KEY v Nastavení.",
            )

    # ── Tray menu ──────────────────────────────────────────────────────

    def _build_tray_menu(self) -> None:
        menu = QMenu()
        menu.addAction("Zobrazit historii", self._show_window)
        menu.addAction("Nastavení", self._open_settings)
        menu.addSeparator()
        menu.addAction("Otevřít log", self.logger.open_log_file)
        menu.addSeparator()
        menu.addAction("Ukončit", self._quit)
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
        if dialog.exec():
            # Po potvrzení nastavení aktualizujeme API klíč v transcriberovi
            self.transcriber.update_api_key(self.settings.effective_api_key())

    def _quit(self) -> None:
        self.logger.log("Ukoncovani aplikace...")
        self._listener.stop()
        self.app.quit()

    # ── Stav ikony ─────────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        self._tray.setIcon(self._icons.get(state, self._icons["idle"]))
        self._state_sig.emit(state)

    # ── Tray notifikace ────────────────────────────────────────────────

    @Slot(str, str)
    def _show_notification(self, title: str, message: str) -> None:
        """Zobrazí bublinu v system tray (volatelné z Qt vlákna)."""
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    def _notify(self, title: str, message: str) -> None:
        """Thread-safe odeslání notifikace přes signál."""
        self._notify_sig.emit(title, message)

    # ── Klávesnice ─────────────────────────────────────────────────────

    def _on_key_press(self, key) -> None:
        if key not in (kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r):
            return
        now = time.time()
        with self._lock:
            diff = now - self._last_ctrl
            self._last_ctrl = now
        if diff < 0.4:
            if not self.recording:
                self._start_recording()
            else:
                self._stop_recording()

    # ── Nahrávání ──────────────────────────────────────────────────────

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
        recorder = AudioRecorder(
            self.logger,
            self.settings.sample_rate,
            self.settings.max_recording_seconds,
        )
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
                self._notify("Voice to Text – chyba", "Normalizace audia selhala.")
                return

            raw_text = self.transcriber.transcribe(
                recorder.normalized_path, self.settings.language
            )
            self.logger.log(f"Puvodni prepis: {raw_text}")

            if not raw_text:
                self.logger.log("Prázdný přepis – pravděpodobně ticho nebo šum.")
                self._notify("Voice to Text", "Přepis je prázdný – nic nebylo rozpoznáno.")
                return

            text_to_paste = raw_text
            if self.settings.use_correction:
                text_to_paste = self.transcriber.correct(
                    raw_text,
                    self.settings.language,
                    custom_prompt=self.settings.get_correction_prompt(self.settings.language),
                )
            if self.settings.translate_to_english:
                text_to_paste = self.transcriber.translate(
                    text_to_paste,
                    self.settings.target_language,
                    custom_prompt=self.settings.get_translation_prompt(self.settings.target_language),
                )
            self.paster.paste(text_to_paste)

        except ValueError as e:
            # Chybí API klíč
            self.logger.log(f"CHYBA – API klíč: {e}")
            self._notify("Voice to Text – chybí API klíč", "Zadejte GROQ_API_KEY v Nastavení.")
        except Exception as e:
            self.logger.log(f"CHYBA v procesu nahravani: {e}")
            self._notify("Voice to Text – chyba", str(e)[:120])
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
            # Cleanup dočasných souborů vždy (při chybě i úspěchu)
            if self.settings.remove_sound_files:
                recorder.cleanup()
            self._recorder = None

