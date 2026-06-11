# whisper.cpp-release

Prebuilt [whisper.cpp](https://github.com/ggml-org/whisper.cpp) binaries for Linux, Windows, and macOS — built and released via GitHub Actions.

Each release includes `whisper-cli` and `whisper-server`.

## Platform support

| Platform | Arch | GPU backend |
|----------|------|-------------|
| Linux | x86_64 | Vulkan |
| Windows | x86_64 | Vulkan |
| macOS (Apple Silicon) | arm64 | CoreML |
| macOS (Intel) | x86_64 | CPU only |

## Download

Get the latest binaries from [GitHub Releases](https://github.com/jiang1997/whisper.cpp-release/releases).

## Python CLI (`whisper_tool`)

A Python helper that downloads default models, locates or fetches prebuilt binaries, and exposes common operations via CLI.

**Requirements:** Python 3.10+, stdlib only (no `pip install` needed).

Run from the repo root — no installation required:

```bash
cd whisper.cpp-release

# One-shot setup: binaries (from local build/release or GitHub Releases) + default models
python3 -m whisper_tool setup

# Check resolved paths
python3 -m whisper_tool status

# Transcribe (VAD enabled by default)
python3 -m whisper_tool transcribe audio.wav

# Start HTTP server
python3 -m whisper_tool serve --host 0.0.0.0 --port 8080
```

### Optional: install as `whisper-tool` command

If you want a global `whisper-tool` shortcut (instead of `python3 -m whisper_tool`):

```bash
pip install -e .        # or: pipx install -e .
whisper-tool status
```

### Default models

| Type | Model | File |
|------|-------|------|
| Whisper | `small.en` | `ggml-small.en.bin` |
| VAD | `silero-v6.2.0` | `ggml-silero-v6.2.0.bin` |

Models are stored in `~/.local/share/whisper-cpp-release/models/`. Binaries downloaded from Releases go to `~/.local/share/whisper-cpp-release/bin/`.

### Commands

```bash
python3 -m whisper_tool setup                              # binaries + default models
python3 -m whisper_tool download binary                    # fetch release binaries only
python3 -m whisper_tool download whisper [MODEL]           # e.g. base.en, small.en
python3 -m whisper_tool download vad [MODEL]               # e.g. silero-v6.2.0
python3 -m whisper_tool transcribe FILE [FILE...] [--no-vad] [-l LANG] [--output-json]
python3 -m whisper_tool transcribe audio.wav -- -pp          # pass extra args to whisper-cli after --
python3 -m whisper_tool serve [--host HOST] [--port PORT] [--no-vad]
python3 -m whisper_tool status
```

Binary discovery order: config `bin_dir` → `PATH` → `whisper.cpp/build/bin/` → `release/whisper-*/` → downloaded bin dir.

## Build locally

```bash
git clone --recurse-submodules https://github.com/jiang1997/whisper.cpp-release.git
cd whisper.cpp-release
make build
```

Override GPU support:
```bash
GGML_VULKAN=0 make build      # CPU-only on Linux/Windows
WHISPER_COREML=0 make build   # CPU-only on macOS ARM
```

## Release

```bash
make release
```

Produces `release/whisper-<version>-<arch>.tar.gz` containing the CLI, server, and shared libraries.

## Acknowledgements

The cross-platform build strategy (platform-specific CMake flags, GPU backend selection, CI build matrix) is based on [Buzz](https://github.com/chidiwilliams/buzz), an offline transcription desktop app that bundles whisper.cpp binaries across Linux, Windows, and macOS.

## License

The build scripts in this repository are MIT-licensed. whisper.cpp itself is [MIT-licensed](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE).
