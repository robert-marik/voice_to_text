"""Logger využívající standardní Python logging modul."""

import logging
import os

from .config import LOG_PATH, APP_DATA_DIR


class Logger:
    def __init__(self, log_path: str = LOG_PATH):
        self.log_path = log_path
        os.makedirs(APP_DATA_DIR, exist_ok=True)

        self._logger = logging.getLogger("voice_to_text")
        if not self._logger.handlers:
            self._logger.setLevel(logging.DEBUG)

            fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

            # Výpis do terminálu
            console = logging.StreamHandler()
            console.setFormatter(fmt)
            self._logger.addHandler(console)

            # Zápis do souboru
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(fmt)
            self._logger.addHandler(file_handler)

    def log(self, message: str) -> None:
        self._logger.info(message)

    def open_log_file(self) -> None:
        """Otevře log soubor v systémovém editoru."""
        import subprocess
        if os.path.exists(self.log_path):
            subprocess.run(["xdg-open", self.log_path])

