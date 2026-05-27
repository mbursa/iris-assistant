# Configuration Reference

This document lists all active configuration options loaded by the app from [src/config.py](src/config.py).

## Load Order

Configuration precedence (last wins):

1. Built-in defaults in code
2. Config file (`config.toml` by default, or `IRIS_CONFIG_FILE`)
3. `.env`
4. Process environment variables

## Required Setting

- `SONIOX_API_KEY` (no default): Soniox API key used for authentication.

## Config File Path

- `IRIS_CONFIG_FILE` (default: `config.toml`): relative path from repository root to the config file.

## Audio Options

- `audio.sample_rate` (env: `IRIS_AUDIO_SAMPLE_RATE`, default: `16000`)
: Microphone sample rate in Hz.

- `audio.channels` (env: `IRIS_AUDIO_CHANNELS`, default: `1`)
: Number of microphone channels.

- `audio.audio_format` (env: `IRIS_AUDIO_FORMAT`, default: `pcm_s16le`)
: Audio frame format sent to Soniox.

## Soniox Options

- `soniox.ws_url` (env: `IRIS_SONIOX_WS_URL`, default: `wss://stt-rt.soniox.com/transcribe-websocket`)
: Soniox realtime websocket endpoint.

- `soniox.model` (env: `IRIS_SONIOX_MODEL`, default: `stt-rt-preview`)
: Soniox realtime model name.

- `soniox.language_hints` (env: `IRIS_SONIOX_LANGUAGE_HINTS`, default: `["en"]`)
: Preferred spoken language hints for speech recognition.
: In env form use comma-separated values, for example `en,cs`.

- `soniox.enable_endpoint_detection` (env: `IRIS_SONIOX_ENABLE_ENDPOINT_DETECTION`, default: `true`)
: Enables endpoint detection to help finalize utterances.

- `soniox.api_key` (env: `SONIOX_API_KEY`, default: empty)
: API key used by Soniox client auth.

## Translation Options

- `translation.source_language` (env: `IRIS_TRANSLATION_SOURCE_LANGUAGE`, default: `en`)
: Expected source language in translation tokens to accept.

- `translation.target_language` (env: `IRIS_TRANSLATION_TARGET_LANGUAGE`, default: `cs`)
: Target language code expected in translation tokens.

- `translation.display_only_final_translations` (env: `IRIS_DISPLAY_ONLY_FINAL_TRANSLATIONS`, default: `true`)
: If enabled, only final translation tokens are shown.

## Trigger Options

- `trigger.detection_buffer_chars` (env: `IRIS_MAGIC_DETECTION_BUFFER_CHARS`, default: `600`)
: Rolling text buffer size used for trigger detection logic.

- `trigger.clear_buffers_on_trigger` (env: `IRIS_CLEAR_BUFFERS_ON_TRIGGER`, default: `true`)
: Clears subtitle buffers when trigger behavior fires.

## UI Options

- `ui.max_lines_on_screen` (env: `IRIS_MAX_LINES_ON_SCREEN`, default: `12`)
: Maximum number of wrapped subtitle lines kept on screen.

- `ui.max_line_chars_approx` (env: `IRIS_MAX_LINE_CHARS_APPROX`, default: `42`)
: Approximate wrap width in characters.

- `ui.window_resizable` (env: `IRIS_WINDOW_RESIZABLE`, default: `true`)
: Allows manual window resize.

- `ui.window_zoomed` (env: `IRIS_WINDOW_ZOOMED`, default: `true`)
: Starts window in zoomed/maximized state when supported.

- `ui.window_keep_on_top` (env: `IRIS_WINDOW_KEEP_ON_TOP`, default: `true`)
: Keeps subtitle window above other windows.

- `ui.window_background_color` (env: `IRIS_WINDOW_BACKGROUND_COLOR`, default: `black`)
: Window background color.

- `ui.window_text_color` (env: `IRIS_WINDOW_TEXT_COLOR`, default: `white`)
: Subtitle text color.

- `ui.window_font_family` (env: `IRIS_WINDOW_FONT_FAMILY`, default: `Segoe UI`)
: Subtitle font family.

- `ui.window_font_size` (env: `IRIS_WINDOW_FONT_SIZE`, default: `68`)
: Subtitle font size.

- `ui.window_font_weight` (env: `IRIS_WINDOW_FONT_WEIGHT`, default: `bold`)
: Subtitle font weight.

- `ui.window_text_padding_x` (env: `IRIS_WINDOW_TEXT_PADDING_X`, default: `70`)
: Horizontal text padding.

- `ui.window_text_padding_y` (env: `IRIS_WINDOW_TEXT_PADDING_Y`, default: `60`)
: Vertical text padding.

- `ui.max_display_chars` (env: `IRIS_MAX_DISPLAY_CHARS`, default: `1200`)
: Max subtitle buffer characters kept before clipping.

## Performance Options

- `performance.ui_tick_ms` (env: `IRIS_UI_TICK_MS`, default: `60`)
: UI refresh interval in milliseconds.

- `performance.audio_queue_max_chunks` (env: `IRIS_AUDIO_QUEUE_MAX_CHUNKS`, default: `300`)
: Max queued microphone audio chunks.

- `performance.clear_subtitles_after_seconds` (env: `IRIS_CLEAR_SUBTITLES_AFTER_SECONDS`, default: `5.0`)
: Subtitle idle timeout value (currently reserved for behavior using this setting).

## Boolean Value Formats

For env vars parsed as booleans, accepted true values are:

- `1`, `true`, `yes`, `y`, `on`

Accepted false values are:

- `0`, `false`, `no`, `n`, `off`

Any other value falls back to that option's default.

## Note About Legacy Keys In config.toml.example

Some keys currently present under `[trigger]` in [config.toml.example](config.toml.example) are not loaded by [src/config.py](src/config.py) right now:

- `magic_phrase`
- `magic_phrase_case_insensitive`
- `start_translation_phrase`
- `trigger1_audio_file`
- `trigger2_audio_file`
- `trigger1_message`
- `trigger2_message`

If needed, these can be reintroduced in the typed settings schema and loader.
