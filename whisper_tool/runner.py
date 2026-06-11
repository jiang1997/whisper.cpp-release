"""Run whisper-cli and whisper-server subprocesses."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from whisper_tool.binaries import (
    BinaryPaths,
    ensure_binaries,
    resolve_binaries_for_run,
)
from whisper_tool.config import Config
from whisper_tool.wsl import arg_for_binary


def _lib_env(bins: BinaryPaths) -> dict[str, str] | None:
    if sys.platform == "win32" or bins.windows:
        return None
    env = os.environ.copy()
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = (
        f"{bins.bin_dir}:{existing}" if existing else str(bins.bin_dir)
    )
    return env


def _require_binaries(cfg: Config) -> BinaryPaths:
    found = resolve_binaries_for_run(cfg)
    if found:
        return found
    return ensure_binaries(cfg)


def _require_whisper_model(cfg: Config) -> Path:
    path = cfg.whisper_model_path()
    if not path.exists():
        raise RuntimeError(
            f"Whisper model not found: {path}\n"
            "Run: whisper-tool setup  (or: whisper-tool download whisper)"
        )
    return path


def _require_vad_model(cfg: Config) -> Path:
    path = cfg.vad_model_path()
    if not path.exists():
        raise RuntimeError(
            f"VAD model not found: {path}\n"
            "Run: whisper-tool setup  (or: whisper-tool download vad)"
        )
    return path


def _path_arg(path: Path, bins: BinaryPaths) -> str:
    return arg_for_binary(path, bins.cli)


def run_transcribe(
    cfg: Config,
    audio_files: list[Path],
    *,
    use_vad: bool = True,
    language: str | None = None,
    translate: bool = False,
    threads: int | None = None,
    output_json: bool = False,
    output_srt: bool = False,
    output_txt: bool = False,
    output_file: str | None = None,
    no_timestamps: bool = False,
    extra_args: list[str] | None = None,
) -> int:
    bins = _require_binaries(cfg)
    model = _require_whisper_model(cfg)

    cmd: list[str] = [str(bins.cli), "-m", _path_arg(model, bins)]

    if use_vad:
        vad = _require_vad_model(cfg)
        cmd.extend(["--vad", "-vm", _path_arg(vad, bins)])

    if language:
        cmd.extend(["-l", language])
    if translate:
        cmd.append("--translate")
    if threads is not None:
        cmd.extend(["-t", str(threads)])
    if output_json:
        cmd.append("--output-json")
    if output_srt:
        cmd.append("--output-srt")
    if output_txt:
        cmd.append("--output-txt")
    if output_file:
        cmd.extend(["--output-file", output_file])
    if no_timestamps:
        cmd.append("--no-timestamps")
    if extra_args:
        cmd.extend(extra_args)

    for f in audio_files:
        cmd.append(_path_arg(f, bins))

    if bins.windows:
        print(f"Using Windows binary (WSL GPU): {bins.cli}")

    result = subprocess.run(cmd, env=_lib_env(bins))
    return result.returncode


def run_serve(
    cfg: Config,
    *,
    use_vad: bool = True,
    host: str = "127.0.0.1",
    port: int = 8080,
    threads: int | None = None,
    extra_args: list[str] | None = None,
) -> int:
    bins = _require_binaries(cfg)
    model = _require_whisper_model(cfg)

    cmd: list[str] = [
        str(bins.server),
        "-m",
        _path_arg(model, bins),
        "--host",
        host,
        "--port",
        str(port),
    ]

    if use_vad:
        vad = _require_vad_model(cfg)
        cmd.extend(["--vad", "-vm", _path_arg(vad, bins)])

    if threads is not None:
        cmd.extend(["-t", str(threads)])
    if extra_args:
        cmd.extend(extra_args)

    print(f"Starting whisper-server on {host}:{port}")
    print(f"  model: {model}")
    if use_vad:
        print(f"  vad:   {cfg.vad_model_path()}")
    if bins.windows:
        print(f"  binary: {bins.server} (Windows/WSL GPU)")

    result = subprocess.run(cmd, env=_lib_env(bins))
    return result.returncode
