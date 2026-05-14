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
