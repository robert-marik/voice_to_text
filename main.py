"""Vstupni bod aplikace."""

import os
import shutil
import sys

from voice_to_text.config import REQUIRED_SYSTEM_TOOLS



def check_dependencies() -> bool:
    ok = True
    for cmd in REQUIRED_SYSTEM_TOOLS:
        if not shutil.which(cmd):
            print(f"CHYBA: Nastroj '{cmd}' neni v systemu dostupny!")
            ok = False
    if not os.environ.get("GROQ_API_KEY"):
        print("CHYBA: Chybi GROQ_API_KEY v prostredi!")
        ok = False
    return ok


def main() -> None:
    if not check_dependencies():
        sys.exit(1)

    import signal
    from PySide6.QtWidgets import QApplication
    from voice_to_text.tray import AppController
    from PySide6.QtCore import QTimer

    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)  # stačí prázdný slot

    app = QApplication(sys.argv)
    app.setApplicationName("Voice to Text")
    app.setQuitOnLastWindowClosed(False)

    controller = AppController(app)  # noqa: F841

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
