"""Download Whisper and VAD models from Hugging Face."""

from __future__ import annotations

from pathlib import Path

from whisper_tool.config import VAD_HF_BASE, WHISPER_HF_BASE, Config
from whisper_tool.download_util import download_file, expectation_for_filename


def whisper_model_url(name: str) -> str:
    return f"{WHISPER_HF_BASE}/ggml-{name}.bin"


def vad_model_url(name: str) -> str:
    return f"{VAD_HF_BASE}/ggml-{name}.bin"


def download_whisper_model(
    cfg: Config,
    name: str | None = None,
    *,
    force: bool = False,
) -> Path:
    model = name or cfg.whisper_model
    dest = cfg.models_dir / f"ggml-{model}.bin"
    download_file(
        whisper_model_url(model),
        dest,
        force=force,
        expectation=expectation_for_filename(dest.name),
    )
    return dest


def download_vad_model(
    cfg: Config,
    name: str | None = None,
    *,
    force: bool = False,
) -> Path:
    model = name or cfg.vad_model
    dest = cfg.models_dir / f"ggml-{model}.bin"
    download_file(
        vad_model_url(model),
        dest,
        force=force,
        expectation=expectation_for_filename(dest.name),
    )
    return dest


def download_default_models(cfg: Config, *, force: bool = False) -> None:
    download_whisper_model(cfg, force=force)
    download_vad_model(cfg, force=force)


def model_status(cfg: Config) -> dict[str, object]:
    whisper_path = cfg.whisper_model_path()
    vad_path = cfg.vad_model_path()
    return {
        "whisper_model": cfg.whisper_model,
        "whisper_path": whisper_path,
        "whisper_exists": whisper_path.exists(),
        "vad_model": cfg.vad_model,
        "vad_path": vad_path,
        "vad_exists": vad_path.exists(),
        "models_dir": cfg.models_dir,
    }
