"""GPU backend selection for prebuilt binaries."""

from __future__ import annotations

import os

from whisper_tool.config import Config

VALID_GPU_BACKENDS = frozenset({"auto", "vulkan", "sycl"})
SYCL_ARTIFACT_SUFFIX = "-sycl"


def resolve_gpu_backend(cfg: Config) -> str:
    raw = os.environ.get("WHISPER_TOOL_GPU_BACKEND", "").strip().lower() or cfg.gpu_backend
    if raw == "auto":
        return "vulkan"
    if raw not in {"vulkan", "sycl"}:
        raise RuntimeError(
            f"Invalid gpu_backend: {raw!r} (use auto, vulkan, or sycl)"
        )
    return raw


def artifact_for_backend(base_artifact: str, gpu_backend: str) -> str:
    if gpu_backend == "sycl":
        if base_artifact in ("linux-x64", "windows-x64"):
            return f"{base_artifact}{SYCL_ARTIFACT_SUFFIX}"
        raise RuntimeError(
            f"SYCL backend is only available for Linux/Windows x86_64, not {base_artifact}"
        )
    return base_artifact
