"""Shared download helpers with integrity checks."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CHUNK_SIZE = 1024 * 64
USER_AGENT = "whisper-tool"

# Known-good metadata for default models (HF ggerganov/whisper.cpp, ggml-org/whisper-vad).
KNOWN_ARTIFACTS: dict[str, tuple[int, str]] = {
    "ggml-small.en.bin": (
        487_614_201,
        "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d",
    ),
    "ggml-silero-v6.2.0.bin": (
        885_098,
        "2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987",
    ),
}

MIN_BYTES_GENERIC = 1024
MIN_BYTES_WHISPER = 10_000_000
MIN_BYTES_VAD = 100_000


@dataclass(frozen=True)
class DownloadExpectation:
    min_bytes: int = MIN_BYTES_GENERIC
    exact_size: int | None = None
    sha256: str | None = None


def expectation_for_filename(name: str) -> DownloadExpectation:
    if name in KNOWN_ARTIFACTS:
        size, digest = KNOWN_ARTIFACTS[name]
        return DownloadExpectation(min_bytes=size, exact_size=size, sha256=digest)
    if name.startswith("ggml-silero"):
        return DownloadExpectation(min_bytes=MIN_BYTES_VAD)
    if name.startswith("ggml-"):
        return DownloadExpectation(min_bytes=MIN_BYTES_WHISPER)
    return DownloadExpectation()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(path: Path, expectation: DownloadExpectation) -> None:
    if not path.exists():
        raise RuntimeError(f"Downloaded file missing: {path}")

    size = path.stat().st_size
    if size < expectation.min_bytes:
        path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Download failed integrity check for {path.name}: "
            f"size {size} bytes is below minimum {expectation.min_bytes}"
        )

    if expectation.exact_size is not None and size != expectation.exact_size:
        path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Download failed integrity check for {path.name}: "
            f"expected {expectation.exact_size} bytes, got {size}"
        )

    if expectation.sha256 is not None:
        actual = sha256_file(path)
        if actual != expectation.sha256:
            path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Download failed integrity check for {path.name}: "
                f"SHA256 mismatch (got {actual})"
            )


def download_file(
    url: str,
    dest: Path,
    *,
    force: bool = False,
    expectation: DownloadExpectation | None = None,
) -> None:
    exp = expectation or expectation_for_filename(dest.name)

    if dest.exists() and not force:
        try:
            verify_artifact(dest, exp)
            print(f"Already exists, skipping: {dest}")
            return
        except RuntimeError:
            print(f"Existing file failed integrity check, re-downloading: {dest}")
            dest.unlink(missing_ok=True)

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    print(f"Downloading {url}")
    print(f"  -> {dest}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        print(
                            f"\r  {mb_done:.1f}/{mb_total:.1f} MiB ({pct}%)",
                            end="",
                            flush=True,
                        )
            if total > 0:
                print()
            if total > 0 and downloaded != total:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Incomplete download for {dest.name}: "
                    f"expected {total} bytes, got {downloaded}"
                )
    except urllib.error.URLError as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {url}: {e}") from e

    tmp.rename(dest)
    verify_artifact(dest, exp)
    print(f"Done: {dest}")
