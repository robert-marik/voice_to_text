[🇨🇿 Česky](README.md) · [🇬🇧 English](README_en.md)

# 🎙️ Voice to Text

> Aplikace pro Linux, která přepisuje hlas pomocí OpenAI Whisper (přes Groq API)
> s volitelnou AI opravou pravopisu a překladem — vše spouštěné dvojitým stiskem
> klávesy `Ctrl`. Komunikace s AI je prostřednictvím souboru typu OPUS, který
> šetří přenášená data a zrychluje odezvu.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41cd52?style=flat-square)](https://doc.qt.io/qtforpython/)
[![Groq](https://img.shields.io/badge/AI-Groq%20API-f55036?style=flat-square)](https://groq.com)
[![Licence](https://img.shields.io/badge/licence-MIT-lightgrey?style=flat-square)](LICENSE)

---

## ✨ Funkce

- **Dvojitý stisk `Ctrl`** spustí a zastaví nahrávání — funguje v jakékoli aplikaci
- **Přepis přes Whisper** pomocí Groq API (`whisper-large-v3-turbo`)
- **AI oprava pravopisu** — opraví překlepy, čárky a gramatiku pomocí LLM
- **Překlad do angličtiny** — volitelný jednokrokový překlad po přepisu
- **Historie přepisů** — trvalý lokální záznam všech nahrávek s možností prohlížení
- **Automatické pozastavení hudby** — pauzuje přehrávač během nahrávání, pak ho obnoví
- **Ikona v systray** — barevně kódovaný stav: 🔵 připraven · 🔴 nahrávám · 🟡 zpracovávám
- **Nativní Qt6 GUI** — okno s historií, dialog nastavení, kopírování do schránky

---

## 📋 Požadavky

### Systémové nástroje

```bash
sudo apt install alsa-utils ffmpeg xclip xdotool playerctl
```

| Nástroj | Účel |
|---|---|
| `arecord` (alsa-utils) | Nahrávání zvuku z mikrofonu |
| `ffmpeg` | Normalizace hlasitosti a převod do Opus |
| `xclip` | Zkopírování textu do schránky |
| `xdotool` | Simulace Ctrl+V pro vložení do aktivního okna |
| `playerctl` | Pozastavení/obnovení přehrávače médií |

### Python závislosti

```bash
pip install groq numpy scipy PySide6 pynput
# nebo přes pyproject.toml:
pip install -e .
```

### API klíč pro Groq

Zaregistrujte se na [console.groq.com](https://console.groq.com) (k dispozici je bezplatný tarif) a exportujte klíč:

```bash
export GROQ_API_KEY="váš_klíč"
```

Pro trvalé nastavení přidejte řádek do `~/.bashrc` nebo `~/.zshrc`.

---

## 🚀 Instalace

```bash
git clone https://github.com/yourname/voice-to-text.git
cd voice-to-text

# Doporučeno: virtuální prostředí
python -m venv .venv
source .venv/bin/activate

# Instalace závislostí
pip install -e .

# Spuštění
python main.py
```

---

## 🎮 Ovládání

| Akce | Výsledek |
|---|---|
| **2× Ctrl** | Zahájí nahrávání |
| **2× Ctrl** znovu | Ukončí nahrávání a spustí přepis |
| **Levý klik na ikonu** | Otevře okno s historií |
| **Pravý klik na ikonu** | Kontextové menu |

Po zastavení nahrávání aplikace:
1. Normalizuje hlasitost audia přes `ffmpeg`
2. Odešle audio do Groq Whisper k přepisu
3. Volitelně opraví pravopis a gramatiku pomocí LLM
4. Volitelně přeloží text do angličtiny
5. Vloží výsledek do aktivního okna přes `xdotool`

---

## ⚙️ Nastavení

Veškerá nastavení jsou dostupná v **dialogu Nastavení** (ikona v systray → Nastavení).

| Nastavení | Možnosti | Výchozí |
|---|---|---|
| Jazyk | Čeština / Angličtina | Čeština |
| Vzorkovací frekvence | 16 kHz (rychlejší) / 44,1 kHz (věrnější) | 44,1 kHz |
| AI oprava pravopisu | Zapnuto / Vypnuto | Zapnuto |
| Překlad do angličtiny | Zapnuto / Vypnuto | Vypnuto |

Nastavení se ukládá do `~/.local/state/voice_to_text/settings.json`.

---

## 📁 Struktura projektu

```
voice_to_text/
├── main.py                        # Vstupní bod — kontrola závislostí + QApplication
├── pyproject.toml                 # Metadata projektu a závislosti
│
└── voice_to_text/
    ├── config.py                  # Konstanty (modely, cesty, limity)
    ├── settings.py                # Uživatelská nastavení + JSON persistence
    ├── history.py                 # Historie přepisů + JSON persistence
    ├── logger.py                  # Časově značkovaný logger
    ├── audio.py                   # Nahrávání (arecord) + normalizace (ffmpeg)
    ├── transcriber.py             # Groq Whisper, LLM korekce a překlad
    ├── clipboard.py               # Kopírování (xclip) + vkládání (xdotool)
    ├── music.py                   # Ovládání přehrávače (playerctl)
    ├── tray.py                    # AppController — QSystemTrayIcon + klávesnice
    │
    └── gui/
        ├── main_window.py         # Okno s historií přepisů
        └── settings_dialog.py     # Dialog nastavení
```

---

## 🗂️ Data a logy

Veškerá data aplikace jsou uložena v `~/.local/state/voice_to_text/`:

| Soubor | Obsah |
|---|---|
| `app.log` | Plný časově značkovaný log událostí |
| `history.json` | Posledních 200 přepisů |
| `settings.json` | Uživatelská nastavení |

Dočasné audio soubory jsou zapisovány do `/tmp/voice_input_XXXX.wav` a po restartu systému se automaticky smažou.

---

## 🔧 Řešení problémů

**Žádný zvuk se nenahrává**
```bash
arecord -l          # Zobrazí dostupná nahrávací zařízení
arecord test.wav    # Otestuje nahrávání ručně
```

**Vkládání nefunguje v některých aplikacích**  
Některé aplikace (např. terminály) blokují simulovaný vstup. Místo toho použijte tlačítko **Kopírovat** v okně s historií.

**`GROQ_API_KEY` nenalezen**
```bash
echo $GROQ_API_KEY   # Mělo by vypsat váš klíč
```

**Ikona v systray se nezobrazuje**  
Na GNOME nainstalujte rozšíření [AppIndicator](https://extensions.gnome.org/extension/615/appindicator-support/).

---

## 📄 Licence

MIT