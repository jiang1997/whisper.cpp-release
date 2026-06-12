"""Remove downloaded user data (models, binaries, config)."""

from __future__ import annotations

import shutil
from pathlib import Path

from whisper_tool.config import Config, config_path, default_models_dir, load_config


def downloads_dir() -> Path:
    return default_models_dir().parent / "downloads"


def clean_targets(
    cfg: Config,
    *,
    models: bool = False,
    binaries: bool = False,
    config: bool = False,
) -> list[Path]:
    targets: list[Path] = []

    if models:
        targets.append(cfg.models_dir)

    if binaries:
        targets.append(cfg.effective_bin_dir())
        targets.append(cfg.effective_windows_bin_dir())
        targets.append(downloads_dir())

    if config:
        targets.append(config_path())

    return targets


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _prune_empty_parents(path: Path, stop_at: Path) -> None:
    current = path.parent
    stop_at = stop_at.resolve()
    while current.resolve() != stop_at and current.exists() and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def run_clean(
    cfg: Config,
    *,
    dry_run: bool = False,
    models: bool = False,
    binaries: bool = False,
    config: bool = False,
) -> int:
    clean_all = not (models or binaries or config)
    do_models = clean_all or models
    do_binaries = clean_all or binaries
    do_config = clean_all or config

    targets = clean_targets(
        cfg,
        models=do_models,
        binaries=do_binaries,
        config=do_config,
    )

    existing = [p for p in targets if p.exists()]
    if not existing:
        print("Nothing to clean.")
        return 0

    print("Will remove:" if dry_run else "Removing:")
    for path in existing:
        print(f"  {path}")

    if dry_run:
        return 0

    for path in existing:
        _remove_path(path)
        if path == config_path():
            _prune_empty_parents(path, path.parent.parent)

    print("Clean complete.")
    return 0


def cmd_clean(args) -> int:
    cfg = load_config()
    return run_clean(
        cfg,
        dry_run=args.dry_run,
        models=args.models,
        binaries=args.binaries,
        config=args.config,
    )
