[🇨🇿 Česky](README.md) · [🇬🇧 English](README_en.md)

# 🎙️ Voice to Text

> A Linux systray application that transcribes your voice using OpenAI Whisper (via Groq API), with optional AI spell correction and translation — all triggered by a double-tap of the `Ctrl` key.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41cd52?style=flat-square)](https://doc.qt.io/qtforpython/)
[![Groq](https://img.shields.io/badge/AI-Groq%20API-f55036?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)](LICENSE)

---

## ✨ Features

- **Double-tap `Ctrl`** to start and stop recording — works in any application
- **Whisper transcription** via Groq API (`whisper-large-v3-turbo`)
- **AI spell correction** — fixes typos, commas, and grammar using an LLM
- **Translation to English** — optional one-step translate after transcription
- **Transcription history** — persistent log of all recordings with full detail view
- **Music auto-pause** — pauses your media player during recording, resumes after
- **System tray icon** — color-coded status: 🔵 idle · 🔴 recording · 🟡 processing
- **Native Qt6 GUI** — settings window, history browser, copy to clipboard

---

## 📋 Requirements

### System tools

```bash
sudo apt install alsa-utils ffmpeg xclip xdotool playerctl
```

| Tool                   | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| `arecord` (alsa-utils) | Captures audio from microphone               |
| `ffmpeg`               | Normalizes volume and converts to Opus       |
| `xclip`                | Copies transcribed text to clipboard         |
| `xdotool`              | Simulates Ctrl+V to paste into active window |
| `playerctl`            | Pauses/resumes media players                 |

### Python dependencies

```bash
pip install groq numpy scipy PySide6 pynput
# or, if you have pyproject.toml:
pip install -e .
```

### Groq API key

Sign up at [console.groq.com](https://console.groq.com) (free tier available) and export your key:

```bash
export GROQ_API_KEY="your_key_here"
```

Add it to your `~/.bashrc` or `~/.zshrc` to make it permanent.

---

## 🚀 Installation

```bash
git clone https://github.com/robert-marik/voice-to-text.git
cd voice-to-text

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run
python main.py
```

---

## 🎮 Usage

| Action                    | Result                        |
| ------------------------- | ----------------------------- |
| **2× Ctrl**               | Start recording               |
| **2× Ctrl** again         | Stop recording and transcribe |
| **Left-click tray icon**  | Open history window           |
| **Right-click tray icon** | Context menu                  |

After the recording stops, the app:
1. Normalizes audio volume via `ffmpeg` and converts to Opus format which is
   optimal for speech audio.
2. Sends the audio to Groq Whisper for transcription
3. Optionally corrects spelling/grammar via LLM
4. Optionally translates to English
5. Pastes the result into your active window via `xdotool`

---

## ⚙️ Configuration

All settings are available in the **Settings dialog** (tray icon → Settings).

| Setting              | Options                                      | Default  |
| -------------------- | -------------------------------------------- | -------- |
| Language             | Czech / English                              | Czech    |
| Sample rate          | 16 kHz (faster) / 44.1 kHz (higher fidelity) | 44.1 kHz |
| AI spell correction  | On / Off                                     | On       |
| Translate to English | On / Off                                     | Off      |

Settings are saved to `~/.local/state/voice_to_text/settings.json`.

---

## 📁 Project Structure

```
voice_to_text/
├── main.py                        # Entry point — dependency check + QApplication
├── pyproject.toml
│
└── voice_to_text/
    ├── config.py                  # Constants (models, paths, timeouts)
    ├── settings.py                # User settings + JSON persistence
    ├── history.py                 # Transcription history + JSON persistence
    ├── logger.py                  # Timestamped logger
    ├── audio.py                   # arecord + ffmpeg normalization
    ├── transcriber.py             # Groq Whisper, LLM correction/translation
    ├── clipboard.py               # xclip + xdotool paste
    ├── music.py                   # playerctl pause/resume
    ├── tray.py                    # AppController: QSystemTrayIcon + keyboard
    │
    └── gui/
        ├── main_window.py         # History browser
        └── settings_dialog.py     # Settings dialog
```

---

## 🗂️ Data & Logs

All application data is stored under `~/.local/state/voice_to_text/`:

| File            | Contents                           |
| --------------- | ---------------------------------- |
| `app.log`       | Full timestamped log of all events |
| `history.json`  | Last 200 transcriptions            |
| `settings.json` | User preferences                   |

---

## 🔧 Troubleshooting

**No audio recorded**
```bash
arecord -l          # List available capture devices
arecord test.wav    # Test recording manually
```

**Paste doesn't work in some apps**
Some applications (e.g. terminals) block simulated input. Use the Copy button in the history window instead.

**`GROQ_API_KEY` not found**
```bash
echo $GROQ_API_KEY   # Should print your key
```

**Tray icon doesn't appear**
On GNOME, install the [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/).

---

## 📄 License

MIT