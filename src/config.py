from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    audio_format: str = "pcm_s16le"


@dataclass(frozen=True)
class SonioxConfig:
    ws_url: str = "wss://stt-rt.soniox.com/transcribe-websocket"
    model: str = "stt-rt-preview"
    language_hints: tuple[str, ...] = ("en",)
    enable_endpoint_detection: bool = True
    api_key: str = ""


@dataclass(frozen=True)
class TranslationConfig:
    source_language: str = "en"
    target_language: str = "cs"
    display_only_final_translations: bool = True


@dataclass(frozen=True)
class TriggerConfig:
    detection_buffer_chars: int = 600
    clear_buffers_on_trigger: bool = True


@dataclass(frozen=True)
class UiConfig:
    max_lines_on_screen: int = 12
    max_line_chars_approx: int = 42
    window_resizable: bool = True
    window_zoomed: bool = True
    window_keep_on_top: bool = True
    window_background_color: str = "black"
    window_text_color: str = "white"
    window_font_family: str = "Segoe UI"
    window_font_size: int = 68
    window_font_weight: str = "bold"
    window_text_padding_x: int = 70
    window_text_padding_y: int = 60
    max_display_chars: int = 1200


@dataclass(frozen=True)
class PerformanceConfig:
    ui_tick_ms: int = 60
    audio_queue_max_chunks: int = 300
    clear_subtitles_after_seconds: float = 5.0


@dataclass(frozen=True)
class Settings:
    audio: AudioConfig = AudioConfig()
    soniox: SonioxConfig = SonioxConfig()
    translation: TranslationConfig = TranslationConfig()
    trigger: TriggerConfig = TriggerConfig()
    ui: UiConfig = UiConfig()
    performance: PerformanceConfig = PerformanceConfig()

    def validate(self) -> None:
        if self.audio.sample_rate <= 0:
            raise ValueError("audio.sample_rate must be > 0")
        if self.audio.channels <= 0:
            raise ValueError("audio.channels must be > 0")
        if not self.soniox.ws_url:
            raise ValueError("soniox.ws_url cannot be empty")
        if not self.soniox.model:
            raise ValueError("soniox.model cannot be empty")
        if not self.soniox.api_key:
            raise ValueError("SONIOX_API_KEY is required")
        if not self.translation.target_language:
            raise ValueError("translation.target_language cannot be empty")
        if self.trigger.detection_buffer_chars <= 0:
            raise ValueError("trigger.detection_buffer_chars must be > 0")
        if self.ui.max_lines_on_screen <= 0:
            raise ValueError("ui.max_lines_on_screen must be > 0")
        if self.ui.max_line_chars_approx <= 0:
            raise ValueError("ui.max_line_chars_approx must be > 0")
        if self.performance.ui_tick_ms <= 0:
            raise ValueError("performance.ui_tick_ms must be > 0")
        if self.performance.audio_queue_max_chunks <= 0:
            raise ValueError("performance.audio_queue_max_chunks must be > 0")


def _to_bool(value: str, *, default: bool) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _to_int(value: str, *, default: int) -> int:
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _to_float(value: str, *, default: float) -> float:
    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return default


def _parse_list(value: str) -> tuple[str, ...]:
    parts = [p.strip() for p in value.split(",")]
    return tuple(p for p in parts if p)


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    if path.suffix.lower() == ".toml":
        if tomllib is None:
            raise RuntimeError("TOML config requires Python 3.11+ or tomllib availability")
        return tomllib.loads(path.read_text(encoding="utf-8"))

    raise ValueError(f"Unsupported config file extension: {path.suffix}")


def _pick(m: Mapping[str, Any], key: str, default: Any) -> Any:
    value = m.get(key, default)
    return default if value is None else value


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent

    dotenv_values = _read_dotenv(root / ".env")
    env = {**dotenv_values, **os.environ}

    config_path = env.get("IRIS_CONFIG_FILE", "config.toml")
    config_file_data = _load_config_file(root / config_path)

    audio_cfg = dict(config_file_data.get("audio", {}))
    soniox_cfg = dict(config_file_data.get("soniox", {}))
    translation_cfg = dict(config_file_data.get("translation", {}))
    trigger_cfg = dict(config_file_data.get("trigger", {}))
    ui_cfg = dict(config_file_data.get("ui", {}))
    performance_cfg = dict(config_file_data.get("performance", {}))

    audio = AudioConfig(
        sample_rate=_to_int(
            env.get("IRIS_AUDIO_SAMPLE_RATE", str(_pick(audio_cfg, "sample_rate", AudioConfig.sample_rate))),
            default=AudioConfig.sample_rate,
        ),
        channels=_to_int(
            env.get("IRIS_AUDIO_CHANNELS", str(_pick(audio_cfg, "channels", AudioConfig.channels))),
            default=AudioConfig.channels,
        ),
        audio_format=env.get("IRIS_AUDIO_FORMAT", str(_pick(audio_cfg, "audio_format", AudioConfig.audio_format))),
    )

    language_hints_default = _pick(soniox_cfg, "language_hints", list(SonioxConfig.language_hints))
    language_hints: tuple[str, ...]
    if "IRIS_SONIOX_LANGUAGE_HINTS" in env:
        language_hints = _parse_list(env["IRIS_SONIOX_LANGUAGE_HINTS"])
    elif isinstance(language_hints_default, list):
        language_hints = tuple(str(x) for x in language_hints_default)
    else:
        language_hints = SonioxConfig.language_hints

    soniox = SonioxConfig(
        ws_url=env.get("IRIS_SONIOX_WS_URL", str(_pick(soniox_cfg, "ws_url", SonioxConfig.ws_url))),
        model=env.get("IRIS_SONIOX_MODEL", str(_pick(soniox_cfg, "model", SonioxConfig.model))),
        language_hints=language_hints,
        enable_endpoint_detection=_to_bool(
            env.get(
                "IRIS_SONIOX_ENABLE_ENDPOINT_DETECTION",
                str(_pick(soniox_cfg, "enable_endpoint_detection", SonioxConfig.enable_endpoint_detection)),
            ),
            default=SonioxConfig.enable_endpoint_detection,
        ),
        api_key=env.get("SONIOX_API_KEY", str(_pick(soniox_cfg, "api_key", SonioxConfig.api_key))).strip(),
    )

    translation = TranslationConfig(
        source_language=env.get(
            "IRIS_TRANSLATION_SOURCE_LANGUAGE",
            str(_pick(translation_cfg, "source_language", TranslationConfig.source_language)),
        ),
        target_language=env.get(
            "IRIS_TRANSLATION_TARGET_LANGUAGE",
            str(_pick(translation_cfg, "target_language", TranslationConfig.target_language)),
        ),
        display_only_final_translations=_to_bool(
            env.get(
                "IRIS_DISPLAY_ONLY_FINAL_TRANSLATIONS",
                str(
                    _pick(
                        translation_cfg,
                        "display_only_final_translations",
                        TranslationConfig.display_only_final_translations,
                    )
                ),
            ),
            default=TranslationConfig.display_only_final_translations,
        ),
    )

    trigger = TriggerConfig(
        detection_buffer_chars=_to_int(
            env.get(
                "IRIS_MAGIC_DETECTION_BUFFER_CHARS",
                str(_pick(trigger_cfg, "detection_buffer_chars", TriggerConfig.detection_buffer_chars)),
            ),
            default=TriggerConfig.detection_buffer_chars,
        ),
        clear_buffers_on_trigger=_to_bool(
            env.get(
                "IRIS_CLEAR_BUFFERS_ON_TRIGGER",
                str(_pick(trigger_cfg, "clear_buffers_on_trigger", TriggerConfig.clear_buffers_on_trigger)),
            ),
            default=TriggerConfig.clear_buffers_on_trigger,
        ),
    )

    ui = UiConfig(
        max_lines_on_screen=_to_int(
            env.get("IRIS_MAX_LINES_ON_SCREEN", str(_pick(ui_cfg, "max_lines_on_screen", UiConfig.max_lines_on_screen))),
            default=UiConfig.max_lines_on_screen,
        ),
        max_line_chars_approx=_to_int(
            env.get(
                "IRIS_MAX_LINE_CHARS_APPROX",
                str(_pick(ui_cfg, "max_line_chars_approx", UiConfig.max_line_chars_approx)),
            ),
            default=UiConfig.max_line_chars_approx,
        ),
        window_resizable=_to_bool(
            env.get("IRIS_WINDOW_RESIZABLE", str(_pick(ui_cfg, "window_resizable", UiConfig.window_resizable))),
            default=UiConfig.window_resizable,
        ),
        window_zoomed=_to_bool(
            env.get("IRIS_WINDOW_ZOOMED", str(_pick(ui_cfg, "window_zoomed", UiConfig.window_zoomed))),
            default=UiConfig.window_zoomed,
        ),
        window_keep_on_top=_to_bool(
            env.get(
                "IRIS_WINDOW_KEEP_ON_TOP",
                str(_pick(ui_cfg, "window_keep_on_top", UiConfig.window_keep_on_top)),
            ),
            default=UiConfig.window_keep_on_top,
        ),
        window_background_color=env.get(
            "IRIS_WINDOW_BACKGROUND_COLOR",
            str(_pick(ui_cfg, "window_background_color", UiConfig.window_background_color)),
        ),
        window_text_color=env.get(
            "IRIS_WINDOW_TEXT_COLOR",
            str(_pick(ui_cfg, "window_text_color", UiConfig.window_text_color)),
        ),
        window_font_family=env.get(
            "IRIS_WINDOW_FONT_FAMILY",
            str(_pick(ui_cfg, "window_font_family", UiConfig.window_font_family)),
        ),
        window_font_size=_to_int(
            env.get("IRIS_WINDOW_FONT_SIZE", str(_pick(ui_cfg, "window_font_size", UiConfig.window_font_size))),
            default=UiConfig.window_font_size,
        ),
        window_font_weight=env.get(
            "IRIS_WINDOW_FONT_WEIGHT",
            str(_pick(ui_cfg, "window_font_weight", UiConfig.window_font_weight)),
        ),
        window_text_padding_x=_to_int(
            env.get(
                "IRIS_WINDOW_TEXT_PADDING_X",
                str(_pick(ui_cfg, "window_text_padding_x", UiConfig.window_text_padding_x)),
            ),
            default=UiConfig.window_text_padding_x,
        ),
        window_text_padding_y=_to_int(
            env.get(
                "IRIS_WINDOW_TEXT_PADDING_Y",
                str(_pick(ui_cfg, "window_text_padding_y", UiConfig.window_text_padding_y)),
            ),
            default=UiConfig.window_text_padding_y,
        ),
        max_display_chars=_to_int(
            env.get("IRIS_MAX_DISPLAY_CHARS", str(_pick(ui_cfg, "max_display_chars", UiConfig.max_display_chars))),
            default=UiConfig.max_display_chars,
        ),
    )

    performance = PerformanceConfig(
        ui_tick_ms=_to_int(
            env.get("IRIS_UI_TICK_MS", str(_pick(performance_cfg, "ui_tick_ms", PerformanceConfig.ui_tick_ms))),
            default=PerformanceConfig.ui_tick_ms,
        ),
        audio_queue_max_chunks=_to_int(
            env.get(
                "IRIS_AUDIO_QUEUE_MAX_CHUNKS",
                str(_pick(performance_cfg, "audio_queue_max_chunks", PerformanceConfig.audio_queue_max_chunks)),
            ),
            default=PerformanceConfig.audio_queue_max_chunks,
        ),
        clear_subtitles_after_seconds=_to_float(
            env.get(
                "IRIS_CLEAR_SUBTITLES_AFTER_SECONDS",
                str(
                    _pick(
                        performance_cfg,
                        "clear_subtitles_after_seconds",
                        PerformanceConfig.clear_subtitles_after_seconds,
                    )
                ),
            ),
            default=PerformanceConfig.clear_subtitles_after_seconds,
        ),
    )

    settings = Settings(
        audio=audio,
        soniox=soniox,
        translation=translation,
        trigger=trigger,
        ui=ui,
        performance=performance,
    )
    settings.validate()
    return settings
