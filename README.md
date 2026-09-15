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
4. Run the translator using either the `uv` or `venv` command below.

Required:

- SONIOX_API_KEY: Soniox API key

Common environment overrides:

- IRIS_CONFIG_FILE
- IRIS_SONIOX_LANGUAGE_HINTS (comma-separated, for example en,cs)
- IRIS_TRANSLATION_SOURCE_LANGUAGE
- IRIS_TRANSLATION_TARGET_LANGUAGE
- IRIS_DISPLAY_ONLY_FINAL_TRANSLATIONS
- IRIS_WINDOW_FONT_SIZE

For a complete reference of configuration options, see `doc/configuration.md` file.

## Run

From the project root, run either executable entry point with `uv`. It reads
the dependencies declared in the script, creates or reuses its managed
environment, and starts the application:

```bash
./translator.py
# or, for console transcription:
./transcriber.py
```

The scripts can also be launched explicitly with `uv run`:

```bash
uv run translator.py
uv run transcriber.py
```

If you chose the traditional `venv` setup, activate it first and run the
scripts with its Python interpreter:

```bash
source .python/bin/activate
python translator.py
python transcriber.py
```

Press Escape/Crtl+C to close the subtitle window.

## Project Layout

- [translator.py](translator.py): entry point
- [src/app.py](src/app.py): app orchestration
- [src/config.py](src/config.py): typed settings loader and validation
- [src/soniox.py](src/soniox.py): Soniox streaming and token handling
- [src/microphone.py](src/microphone.py): microphone capture
- [src/window.py](src/window.py): Tkinter subtitle window
- [src/subtitles.py](src/subtitles.py): shared subtitle state

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
