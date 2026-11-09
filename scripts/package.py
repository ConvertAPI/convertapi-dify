"""Build dist/convertapi-<version>.difypkg the way `dify plugin package` does.

A .difypkg is a plain deflate zip of the plugin directory minus the paths in
.difyignore. Prefer the official CLI when it is available:
    dify plugin package . -o dist/convertapi-<version>.difypkg
This script produces the same layout without the Go binary.
"""

from __future__ import annotations

import fnmatch
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 50 * 1024 * 1024  # the CLI's default limit


def load_ignore() -> list[str]:
    lines = (ROOT / ".difyignore").read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def ignored(rel: str, patterns: list[str]) -> bool:
    parts = rel.split("/")
    for pattern in patterns:
        if pattern.endswith("/"):
            name = pattern.rstrip("/")
            if any(fnmatch.fnmatch(p, name) for p in parts[:-1]):
                return True
        elif "/" in pattern:
            if fnmatch.fnmatch(rel, pattern.lstrip("/")):
                return True
        elif any(fnmatch.fnmatch(p, pattern) for p in parts):
            return True
    return False


def manifest_version() -> str:
    for line in (ROOT / "manifest.yaml").read_text().splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise SystemExit("manifest.yaml has no top-level version")


def main() -> int:
    patterns = load_ignore()
    files = sorted(
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and not ignored(p.relative_to(ROOT).as_posix(), patterns)
    )
    out = ROOT / "dist" / f"convertapi-{manifest_version()}.difypkg"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, (ROOT / rel).read_bytes())
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"package is {size} bytes, over the {MAX_BYTES} limit")
    print(f"{out.relative_to(ROOT)} ({size} bytes, {len(files)} files)")
    for rel in files:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
