"""Vstupni bod aplikace."""

import shutil
import sys


def check_dependencies() -> bool:
    from voice_to_text.config import REQUIRED_SYSTEM_TOOLS
    ok = True
    for cmd in REQUIRED_SYSTEM_TOOLS:
        if not shutil.which(cmd):
            print(f"CHYBA: Nastroj '{cmd}' neni v systemu dostupny!")
            ok = False
    if not ok:
        return False
    return True


def main() -> None:
    if not check_dependencies():
        sys.exit(1)

    import signal
    from PySide6.QtWidgets import QApplication
    from voice_to_text.tray import AppController
    from PySide6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setApplicationName("Voice to Text")
    app.setQuitOnLastWindowClosed(False)

    controller = AppController(app)  # noqa: F841

    signal.signal(signal.SIGINT, lambda *_: app.quit())

    # Jeden timer pro správné zpracování SIGINT v Qt smyčce
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
