"""WSL detection and Windows interop helpers."""

from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def prefer_windows_binaries() -> bool:
    """Whether to prefer Windows .exe binaries (default: yes on WSL)."""
    import os

    if os.environ.get("WHISPER_TOOL_LINUX_BINARIES", "").lower() in ("1", "true", "yes"):
        return False
    return is_wsl()


def is_windows_binary(path: Path) -> bool:
    return path.suffix.lower() == ".exe"


def to_windows_path(path: Path) -> str:
    path = path.resolve()
    try:
        result = subprocess.run(
            ["wslpath", "-w", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "wslpath not found; required to run Windows binaries from WSL"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"wslpath failed for {path}: {e.stderr.strip()}") from e
    return result.stdout.strip()


def arg_for_binary(path: Path, binary: Path) -> str:
    if is_windows_binary(binary) and is_wsl():
        return to_windows_path(path)
    return str(path)
