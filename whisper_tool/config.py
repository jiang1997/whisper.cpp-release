"""Configuration paths and defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "whisper-cpp-release"
DEFAULT_WHISPER_MODEL = "small.en"
DEFAULT_VAD_MODEL = "silero-v6.2.0"

WHISPER_HF_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
VAD_HF_BASE = "https://huggingface.co/ggml-org/whisper-vad/resolve/main"

GITHUB_REPO = "jiang1997/whisper.cpp-release"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def config_path() -> Path:
    return _xdg_config_home() / APP_NAME / "config.json"


def default_models_dir() -> Path:
    return _xdg_data_home() / APP_NAME / "models"


def default_bin_dir() -> Path:
    return _xdg_data_home() / APP_NAME / "bin"


def default_windows_bin_dir() -> Path:
    return _xdg_data_home() / APP_NAME / "bin-win"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass
class Config:
    whisper_model: str = DEFAULT_WHISPER_MODEL
    vad_model: str = DEFAULT_VAD_MODEL
    models_dir: Path = field(default_factory=default_models_dir)
    bin_dir: Path = field(default_factory=default_bin_dir)
    bin_dir_win: Path = field(default_factory=default_windows_bin_dir)
    bin_dir_override: Path | None = None
    use_windows_binaries: bool | None = None

    def whisper_model_path(self) -> Path:
        return self.models_dir / f"ggml-{self.whisper_model}.bin"

    def vad_model_path(self) -> Path:
        return self.models_dir / f"ggml-{self.vad_model}.bin"

    def effective_bin_dir(self) -> Path:
        """Directory used for Linux binary discovery and installs."""
        return self.bin_dir_override or self.bin_dir

    def effective_windows_bin_dir(self) -> Path:
        """Directory used for Windows binary discovery and installs (WSL)."""
        return self.bin_dir_win

    def prefer_windows_binaries(self) -> bool:
        if self.use_windows_binaries is not None:
            return self.use_windows_binaries
        from whisper_tool.wsl import prefer_windows_binaries

        return prefer_windows_binaries()


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config()

    data = json.loads(path.read_text(encoding="utf-8"))
    cfg = Config()
    if "whisper_model" in data:
        cfg.whisper_model = data["whisper_model"]
    if "vad_model" in data:
        cfg.vad_model = data["vad_model"]
    if "models_dir" in data:
        cfg.models_dir = Path(data["models_dir"])
    if "bin_dir" in data:
        cfg.bin_dir = Path(data["bin_dir"])
    if "bin_dir_win" in data:
        cfg.bin_dir_win = Path(data["bin_dir_win"])
    if "bin_dir_override" in data and data["bin_dir_override"]:
        cfg.bin_dir_override = Path(data["bin_dir_override"])
    if "use_windows_binaries" in data:
        cfg.use_windows_binaries = data["use_windows_binaries"]
    return cfg


def save_config(cfg: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "whisper_model": cfg.whisper_model,
        "vad_model": cfg.vad_model,
        "models_dir": str(cfg.models_dir),
        "bin_dir": str(cfg.bin_dir),
        "bin_dir_win": str(cfg.bin_dir_win),
        "bin_dir_override": str(cfg.bin_dir_override) if cfg.bin_dir_override else None,
        "use_windows_binaries": cfg.use_windows_binaries,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
