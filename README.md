# Iris Assistant

Real-time speech-to-translation subtitle assistant powered by Soniox.

The app captures microphone audio, streams it to Soniox over WebSocket, and shows translated subtitles in a fullscreen-style desktop window.

## Features

- Real-time microphone capture (PCM 16-bit, mono)
- Soniox live transcription and one-way translation
- Large subtitle window for on-screen readability
- Typed, validated configuration with layered overrides

## Requirements

- Python 3.11+
- A valid Soniox API key
- Audio stack support for microphone input (PortAudio backend)

## Installation

1. Clone this repository.
2. Ensure the system audio libraries are available.

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev
```

Choose one of the following Python environment setups.

### Option 1: uv

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/). The
dependencies are declared in both entry-point scripts and will be installed
automatically by `uv` when the application starts.

### Option 2: traditional venv

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .python
source .python/bin/activate
.python/bin/python -m pip install --upgrade pip
.python/bin/python -m pip install numpy sounddevice websockets pygame
```

## Configuration

Configuration is loaded in this order (later wins):

1. Built-in defaults
2. config.toml
3. .env
4. Process environment variables

Quick setup:

1. Copy .env.example to .env
2. Set SONIOX_API_KEY in .env
3. Optional: copy config.toml.example to config.toml and tune values
4. Run the translator with its source language using either the `uv` or `venv` command below.

Required:

- SONIOX_API_KEY: Soniox API key

Common environment overrides:

- IRIS_CONFIG_FILE
- IRIS_DISPLAY_ONLY_FINAL_TRANSLATIONS
- IRIS_WINDOW_FONT_SIZE

For a complete reference of configuration options, see `doc/configuration.md` file.

## Run

From the project root, run either executable entry point with `uv`. It reads
the dependencies declared in the script, creates or reuses its managed
environment, and starts the application:

```bash
./translator.py --source-lang cs
# or, for console transcription:
./transcriber.py --source-lang cs
```

The scripts can also be launched explicitly with `uv run`:

```bash
uv run translator.py --source-lang en
uv run transcriber.py --source-lang en
```

If you chose the traditional `venv` setup, activate it first and run the
scripts with its Python interpreter:

```bash
source .python/bin/activate
python translator.py --source-lang cs
python transcriber.py --source-lang cs
```

Both entry points require `--source-lang`. The translator also accepts an
optional `--target-lang`:

```bash
./translator.py --source-lang de --target-lang en
```

Language codes are case-insensitive, and `cz` is normalized to `cs`. When
`--target-lang` is omitted, a Czech source (`cs` or `cz`) translates to English;
every other source language translates to Czech.

Press Escape/Crtl+C to close the subtitle window.

## Project Layout

- [translator.py](translator.py): translated-subtitle entry point
- [transcriber.py](transcriber.py): speaker-aware console-transcription entry point
- [src/app.py](src/app.py): orchestration for both entry points
- [src/config.py](src/config.py): typed non-language settings loader and validation
- [src/languages.py](src/languages.py): language-code normalization and translation defaults
- [src/soniox.py](src/soniox.py): shared Soniox streaming and translation-token handling
- [src/transcription.py](src/transcription.py): transcriber CLI options and transcript rendering
- [src/microphone.py](src/microphone.py): shared microphone capture
- [src/subtitles.py](src/subtitles.py): thread-safe translated-subtitle state
- [src/window.py](src/window.py): Tkinter subtitle window
- [config.toml.example](config.toml.example): example non-secret application configuration
- [doc/configuration.md](doc/configuration.md): complete configuration reference

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
