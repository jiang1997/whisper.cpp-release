"""CLI entry point for whisper-tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from whisper_tool import __version__
from whisper_tool.binaries import (
    binary_status,
    download_binaries,
    ensure_binaries,
    platform_artifact,
)
from whisper_tool.config import config_path, load_config, save_config
from whisper_tool.models import (
    download_default_models,
    download_vad_model,
    download_whisper_model,
    model_status,
)
from whisper_tool.runner import run_serve, run_transcribe


def _cmd_setup(args: argparse.Namespace) -> int:
    cfg = load_config()
    cfg.models_dir.mkdir(parents=True, exist_ok=True)
    cfg.effective_bin_dir().mkdir(parents=True, exist_ok=True)

    print("==> Ensuring binaries")
    bins = ensure_binaries(cfg.effective_bin_dir(), force=args.force)
    print(f"    cli:    {bins.cli}")
    print(f"    server: {bins.server}")

    print("==> Downloading default models")
    download_default_models(cfg, force=args.force)

    save_config(cfg)
    print("==> Setup complete")
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    cfg = load_config()
    cfg.models_dir.mkdir(parents=True, exist_ok=True)
    cfg.effective_bin_dir().mkdir(parents=True, exist_ok=True)

    if args.target == "binary":
        download_binaries(cfg.effective_bin_dir(), force=args.force)
    elif args.target == "whisper":
        download_whisper_model(cfg, args.model, force=args.force)
    elif args.target == "vad":
        download_vad_model(cfg, args.model, force=args.force)
    else:
        print(f"Unknown download target: {args.target}", file=sys.stderr)
        return 1

    save_config(cfg)
    return 0


def _cmd_transcribe(args: argparse.Namespace) -> int:
    cfg = load_config()
    files = [Path(f) for f in args.files]
    for f in files:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 1

    try:
        return run_transcribe(
            cfg,
            files,
            use_vad=not args.no_vad,
            language=args.language,
            translate=args.translate,
            threads=args.threads,
            output_json=args.output_json,
            output_srt=args.output_srt,
            output_txt=args.output_txt,
            output_file=args.output_file,
            no_timestamps=args.no_timestamps,
            extra_args=getattr(args, "passthrough", None) or None,
        )
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    cfg = load_config()
    try:
        return run_serve(
            cfg,
            use_vad=not args.no_vad,
            host=args.host,
            port=args.port,
            threads=args.threads,
            extra_args=getattr(args, "passthrough", None) or None,
        )
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1


def _cmd_status(_args: argparse.Namespace) -> int:
    cfg = load_config()
    bstat = binary_status(cfg.effective_bin_dir())
    mstat = model_status(cfg)

    print(f"whisper-tool {__version__}")
    print(f"config:           {config_path()}")
    print(f"platform:         {platform_artifact()}")
    print()
    print("binaries:")
    print(f"  found:          {bstat['found']}")
    print(f"  source:         {bstat['source'] or '(not found)'}")
    print(f"  cli:            {bstat['cli'] or '(not found)'}")
    print(f"  server:         {bstat['server'] or '(not found)'}")
    print(f"  bin_dir:        {bstat['bin_dir']}")
    print()
    print("models:")
    print(f"  models_dir:     {mstat['models_dir']}")
    print(f"  whisper:        {mstat['whisper_model']} -> {mstat['whisper_path']}")
    print(f"    exists:       {mstat['whisper_exists']}")
    print(f"  vad:            {mstat['vad_model']} -> {mstat['vad_path']}")
    print(f"    exists:       {mstat['vad_exists']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whisper-tool",
        description="Download whisper.cpp binaries/models and run transcription.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="Download binaries (if needed) and default models")
    p_setup.add_argument("--force", action="store_true", help="Re-download even if files exist")
    p_setup.set_defaults(func=_cmd_setup)

    p_dl = sub.add_parser("download", help="Download binaries or models")
    p_dl.add_argument(
        "target",
        choices=["binary", "whisper", "vad"],
        help="What to download",
    )
    p_dl.add_argument(
        "model",
        nargs="?",
        default=None,
        help="Model name (for whisper/vad targets; uses defaults if omitted)",
    )
    p_dl.add_argument("--force", action="store_true", help="Re-download even if files exist")
    p_dl.set_defaults(func=_cmd_download)

    p_tr = sub.add_parser("transcribe", help="Transcribe audio file(s)")
    p_tr.add_argument("files", nargs="+", help="Audio files (wav, mp3, flac, ogg)")
    p_tr.add_argument("--no-vad", action="store_true", help="Disable VAD preprocessing")
    p_tr.add_argument("-l", "--language", default=None, help="Spoken language (e.g. en, auto)")
    p_tr.add_argument("--translate", action="store_true", help="Translate to English")
    p_tr.add_argument("-t", "--threads", type=int, default=None, help="Thread count")
    p_tr.add_argument("--output-json", action="store_true", help="Write JSON output")
    p_tr.add_argument("--output-srt", action="store_true", help="Write SRT subtitles")
    p_tr.add_argument("--output-txt", action="store_true", help="Write plain text output")
    p_tr.add_argument("-o", "--output-file", default=None, help="Output file base name")
    p_tr.add_argument("--no-timestamps", action="store_true", help="Omit timestamps")
    p_tr.set_defaults(func=_cmd_transcribe, passthrough=[])

    p_sv = sub.add_parser("serve", help="Start whisper-server HTTP service")
    p_sv.add_argument("--no-vad", action="store_true", help="Disable VAD")
    p_sv.add_argument("--host", default="127.0.0.1", help="Bind host")
    p_sv.add_argument("--port", type=int, default=8080, help="Bind port")
    p_sv.add_argument("-t", "--threads", type=int, default=None, help="Thread count")
    p_sv.set_defaults(func=_cmd_serve, passthrough=[])

    p_st = sub.add_parser("status", help="Show binary and model status")
    p_st.set_defaults(func=_cmd_status)

    return parser


def _split_passthrough(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv at '--' for whisper-cli/server passthrough args."""
    if argv and argv[0] in ("transcribe", "serve") and "--" in argv:
        idx = argv.index("--")
        return argv[:idx], argv[idx + 1 :]
    return argv, []


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    cli_argv, passthrough = _split_passthrough(raw)
    parser = build_parser()
    args = parser.parse_args(cli_argv)
    if passthrough:
        args.passthrough = passthrough
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
