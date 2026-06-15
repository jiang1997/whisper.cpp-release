# whisper.cpp-release

Prebuilt [whisper.cpp](https://github.com/ggml-org/whisper.cpp) binaries for Linux, Windows, and macOS — built and released via GitHub Actions.

Each release includes `whisper-cli` and `whisper-server`.

## Platform support

| Platform | Arch | GPU backend |
|----------|------|-------------|
| Linux | x86_64 | Vulkan (release), SYCL (local build) |
| Windows | x86_64 | Vulkan |
| macOS (Apple Silicon) | arm64 | CoreML |
| macOS (Intel) | x86_64 | CPU only |

## Download

Get the latest binaries from [GitHub Releases](https://github.com/jiang1997/whisper.cpp-release/releases).

## Python CLI (`whisper_tool`)

A Python helper that downloads default models, locates or fetches prebuilt binaries, and exposes common operations via CLI.

**Requirements:** Python 3.10+, stdlib only (no `pip install` needed).

Run the launcher script from the repo — works from any working directory:

```bash
cd whisper.cpp-release

# One-shot setup: binaries (from local build/release or GitHub Releases) + default models
./bin/whisper-tool setup

# Check resolved paths
./bin/whisper-tool status

# Transcribe (VAD enabled by default)
./bin/whisper-tool transcribe audio.wav

# Start HTTP server
./bin/whisper-tool serve --host 0.0.0.0 --port 8080
```

Install to PATH (optional):

```bash
ln -s "$(pwd)/bin/whisper-tool" ~/.local/bin/whisper-tool
whisper-tool status
```

Equivalent without the launcher: `python3 -m whisper_tool ...` (must run from repo root, or set `PYTHONPATH`).

Another optional install via pip: `pip install -e .` / `pipx install -e .` also provides a `whisper-tool` command.

### Default models

| Type | Model | File |
|------|-------|------|
| Whisper | `small.en` | `ggml-small.en.bin` |
| VAD | `silero-v6.2.0` | `ggml-silero-v6.2.0.bin` |

Default data locations:

| Platform | Root directory |
|----------|----------------|
| Linux / macOS / WSL | `~/.local/share/whisper-cpp-release/` |
| Windows | `%LOCALAPPDATA%\whisper-cpp-release\` |

Under the root: `models/`, `bin/` (Linux/macOS/Windows), `bin-win/` (WSL Windows `.exe`), `downloads/`. Config is `config.json` in the root on Windows, or `~/.config/whisper-cpp-release/config.json` on Linux/macOS/WSL.

### WSL: use Windows binaries for Vulkan GPU

On WSL, the tool automatically prefers Windows `whisper-cli.exe` / `whisper-server.exe` so inference can use Windows Vulkan drivers. `setup` downloads the `windows-x64` release into `bin-win/`. Model and audio paths are converted via `wslpath` when calling `.exe`.

```bash
./bin/whisper-tool setup      # downloads windows-x64 binaries on WSL
./bin/whisper-tool status     # shows wsl: true, windows_binary: true
./bin/whisper-tool transcribe audio.wav
```

Force Linux binaries (CPU only): `WHISPER_TOOL_LINUX_BINARIES=1 ./bin/whisper-tool setup`

### Intel GPU: SYCL backend (local build)

SYCL is **not** built or published in GitHub Actions releases (the CI compile is too memory-heavy). Build locally on Intel CPU/GPU systems with oneAPI installed:

```bash
source /opt/intel/oneapi/setvars.sh   # or use Nix: nix shell nixpkgs#intel-oneapi-toolkit ...
GGML_SYCL=1 make build
GGML_SYCL=1 make release            # release/whisper-<version>-<arch>-sycl.tar.gz
```

Then point whisper-tool at the local build (copy into `bin/`, or use a local `release/whisper-*-sycl/` directory). Runtime requires Intel oneAPI + Level Zero on the target machine.

```bash
./bin/whisper-tool status   # discovers local release/whisper-*-sycl/ if present
```

### Commands

```bash
./bin/whisper-tool setup                              # binaries + default models
./bin/whisper-tool download binary                    # fetch release binaries only
./bin/whisper-tool download whisper [MODEL]           # e.g. base.en, small.en
./bin/whisper-tool download vad [MODEL]               # e.g. silero-v6.2.0
./bin/whisper-tool transcribe FILE [FILE...] [--no-vad] [-l LANG] [--output-json]
./bin/whisper-tool transcribe audio.wav -- -pp          # pass extra args to whisper-cli after --
./bin/whisper-tool serve [--host HOST] [--port PORT] [--no-vad]
./bin/whisper-tool status
./bin/whisper-tool clean [--dry-run] [--models] [--binaries] [--config]
```

`clean` removes downloaded user data from the platform-specific directories above. Without flags it removes everything; use `--dry-run` to preview.

Binary discovery order:

- **WSL (default):** `bin-win/` → `whisper-cli.exe` on `PATH` → `release/whisper-*-windows-x64/` → fallback to Linux `bin/`
- **Linux/macOS:** config `bin_dir` → `PATH` → `whisper.cpp/build/bin/` → `release/whisper-*/` → downloaded bin dir

## Build locally

```bash
git clone --recurse-submodules https://github.com/jiang1997/whisper.cpp-release.git
cd whisper.cpp-release
make build
```

Override GPU support:
```bash
GGML_VULKAN=0 make build      # CPU-only on Linux/Windows
GGML_SYCL=1 make build        # Intel SYCL on Linux/Windows (oneAPI required)
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
