"""Discover or download whisper-cli / whisper-server binaries."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from whisper_tool.config import GITHUB_API_LATEST, repo_root
from whisper_tool.download_util import DownloadExpectation, download_file
from whisper_tool.wsl import is_wsl, prefer_windows_binaries

EXE_EXT = ".exe" if sys.platform == "win32" else ""


@dataclass
class BinaryPaths:
    cli: Path
    server: Path
    source: str
    bin_dir: Path
    windows: bool = False


def _cli_name(*, windows: bool = False) -> str:
    if windows or sys.platform == "win32":
        return "whisper-cli.exe"
    return "whisper-cli"


def _server_name(*, windows: bool = False) -> str:
    if windows or sys.platform == "win32":
        return "whisper-server.exe"
    return "whisper-server"


def platform_artifact(*, prefer_windows: bool | None = None) -> str:
    if prefer_windows is None:
        prefer_windows = prefer_windows_binaries()

    system = sys.platform
    machine = platform.machine().lower()

    if system == "linux":
        if prefer_windows and is_wsl():
            if machine in ("x86_64", "amd64"):
                return "windows-x64"
            raise RuntimeError(f"WSL Windows binaries require x86_64, got: {machine}")
        if machine in ("x86_64", "amd64"):
            return "linux-x64"
        raise RuntimeError(f"Unsupported Linux architecture: {machine}")

    if system == "win32":
        if machine in ("x86_64", "amd64"):
            return "windows-x64"
        raise RuntimeError(f"Unsupported Windows architecture: {machine}")

    if system == "darwin":
        if machine == "arm64":
            return "macos-arm64"
        if machine in ("x86_64", "amd64"):
            return "macos-x64"
        raise RuntimeError(f"Unsupported macOS architecture: {machine}")

    raise RuntimeError(f"Unsupported platform: {system} {machine}")


def _which(name: str) -> Path | None:
    found = shutil.which(name)
    return Path(found) if found else None


def _check_pair(bin_dir: Path, *, windows: bool) -> BinaryPaths | None:
    cli = bin_dir / _cli_name(windows=windows)
    server = bin_dir / _server_name(windows=windows)

    if sys.platform == "win32" and windows:
        if not cli.exists():
            cli = bin_dir / "Release" / "whisper-cli.exe"
        if not server.exists():
            server = bin_dir / "Release" / "whisper-server.exe"

    if cli.exists() and server.exists():
        return BinaryPaths(
            cli=cli,
            server=server,
            source=str(bin_dir),
            bin_dir=bin_dir,
            windows=windows,
        )
    return None


def _release_dirs(root: Path, *, windows: bool | None = None) -> list[Path]:
    release_dir = root / "release"
    if not release_dir.is_dir():
        return []

    dirs: list[Path] = []
    for child in sorted(release_dir.iterdir()):
        if not child.is_dir() or not child.name.startswith("whisper-"):
            continue
        name = child.name.lower()
        if windows is True and "windows" not in name:
            continue
        if windows is False and "windows" in name:
            continue
        dirs.append(child)
    return dirs


def _search_dirs(cfg_bin_dir: Path | None, *, windows: bool) -> list[Path]:
    dirs: list[Path] = []
    root = repo_root()

    if cfg_bin_dir:
        dirs.append(cfg_bin_dir)

    if windows:
        found_cli = _which("whisper-cli.exe")
        if found_cli:
            dirs.append(found_cli.parent)
    else:
        for name in (_cli_name(windows=False), "whisper-cli"):
            found = _which(name)
            if found:
                dirs.append(found.parent)

        dirs.append(root / "whisper.cpp" / "build" / "bin")

    if sys.platform == "win32":
        dirs.append(root / "whisper.cpp" / "build" / "bin" / "Release")

    dirs.extend(_release_dirs(root, windows=windows if is_wsl() else None))

    if cfg_bin_dir is None:
        from whisper_tool.config import default_bin_dir, default_windows_bin_dir

        dirs.append(
            default_windows_bin_dir() if windows else default_bin_dir()
        )

    seen: set[Path] = set()
    unique: list[Path] = []
    for d in dirs:
        resolved = d.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(d)
    return unique


def resolve_binaries(
    cfg_bin_dir: Path | None = None,
    *,
    prefer_windows: bool | None = None,
    allow_linux_fallback: bool = False,
) -> BinaryPaths | None:
    if prefer_windows is None:
        prefer_windows = prefer_windows_binaries()

    if prefer_windows:
        for d in _search_dirs(cfg_bin_dir, windows=True):
            if result := _check_pair(d, windows=True):
                return result
        if not allow_linux_fallback:
            return None

    for d in _search_dirs(cfg_bin_dir, windows=False):
        if result := _check_pair(d, windows=False):
            return result

    return None


def _fetch_latest_release_asset(artifact: str) -> tuple[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "whisper-tool",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(GITHUB_API_LATEST, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "unknown")
    for asset in data.get("assets", []):
        name = asset["name"]
        if artifact in name and (name.endswith(".tar.gz") or name.endswith(".zip")):
            return asset["browser_download_url"], tag

    available = [a["name"] for a in data.get("assets", [])]
    raise RuntimeError(
        f"No release asset found for '{artifact}'. Available: {available or '(none)'}"
    )


def _extract_archive(archive: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)

    if archive.suffix == ".gz" and archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(dest_dir)
    elif archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest_dir)
    else:
        raise RuntimeError(f"Unsupported archive format: {archive}")

    for child in dest_dir.iterdir():
        if child.is_dir() and child.name.startswith("whisper-"):
            for item in child.iterdir():
                target = dest_dir / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                shutil.move(str(item), str(dest_dir))
            child.rmdir()
            break


def download_binaries(
    dest_dir: Path,
    *,
    force: bool = False,
    prefer_windows: bool | None = None,
) -> BinaryPaths:
    windows = prefer_windows if prefer_windows is not None else prefer_windows_binaries()
    existing = _check_pair(dest_dir, windows=windows)
    if existing and not force:
        print(f"Binaries already present in {dest_dir}")
        return existing

    artifact = platform_artifact(prefer_windows=windows)
    url, tag = _fetch_latest_release_asset(artifact)
    print(f"Latest release: {tag} ({artifact})")

    archive_name = url.rsplit("/", 1)[-1]
    archive_path = dest_dir.parent / "downloads" / archive_name
    download_file(
        url,
        archive_path,
        force=force,
        expectation=DownloadExpectation(min_bytes=100_000),
    )

    if force and dest_dir.exists():
        for p in dest_dir.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

    _extract_archive(archive_path, dest_dir)

    if not windows and sys.platform != "win32":
        for name in (_cli_name(windows=False), _server_name(windows=False)):
            path = dest_dir / name
            if path.exists():
                path.chmod(path.stat().st_mode | 0o111)

    result = _check_pair(dest_dir, windows=windows)
    if not result:
        raise RuntimeError(f"Failed to find binaries after extracting to {dest_dir}")

    print(f"Binaries installed to {dest_dir}")
    return result


def install_dir_for_config(cfg) -> Path:
    if cfg.prefer_windows_binaries():
        return cfg.effective_windows_bin_dir()
    return cfg.effective_bin_dir()


def ensure_binaries(cfg, *, force: bool = False) -> BinaryPaths:
    prefer_win = cfg.prefer_windows_binaries()
    install_dir = install_dir_for_config(cfg)
    found = resolve_binaries(install_dir, prefer_windows=prefer_win)
    if found and not force:
        return found

    install_dir.mkdir(parents=True, exist_ok=True)
    return download_binaries(install_dir, force=force, prefer_windows=prefer_win)


def resolve_binaries_for_run(cfg) -> BinaryPaths | None:
    prefer_win = cfg.prefer_windows_binaries()
    install_dir = install_dir_for_config(cfg)
    found = resolve_binaries(install_dir, prefer_windows=prefer_win)
    if found:
        return found
    if prefer_win:
        return resolve_binaries(
            cfg.effective_bin_dir(),
            prefer_windows=False,
            allow_linux_fallback=True,
        )
    return None


def binary_status(cfg) -> dict[str, object]:
    prefer_win = cfg.prefer_windows_binaries()
    install_dir = install_dir_for_config(cfg)
    found = resolve_binaries_for_run(cfg)
    artifact = platform_artifact(prefer_windows=prefer_win)
    if prefer_win and is_wsl():
        artifact = f"{artifact} (WSL)"

    linux_fallback = bool(
        found and prefer_win and not found.windows
    )

    return {
        "wsl": is_wsl(),
        "prefer_windows": prefer_win,
        "platform_artifact": artifact,
        "cli": found.cli if found else None,
        "server": found.server if found else None,
        "windows_binary": found.windows if found else False,
        "linux_fallback": linux_fallback,
        "source": found.source if found else None,
        "found": found is not None,
        "bin_dir": found.bin_dir if found else install_dir,
    }
