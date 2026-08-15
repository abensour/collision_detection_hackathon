#!/usr/bin/env python3
"""Rebuild student_bundle.zip — the package Colab downloads besides the notebook.

Run from the repo root after changing student_solution.py, the toolkit, catalog,
README, or requirements.txt:

    python3 build_student_bundle.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP_PATH = ROOT / "student_bundle.zip"

INCLUDE_FILES = (
    "student_solution.py",
    "spacetrack_data.json",
    "requirements.txt",
    "README.md",
)


def main() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_FILES:
            zf.write(ROOT / rel, rel)
        toolkit = ROOT / "conjunction_toolkit"
        for path in sorted(toolkit.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc"} or path.name == ".DS_Store":
                continue
            zf.write(path, path.relative_to(ROOT).as_posix())

    names = zipfile.ZipFile(ZIP_PATH).namelist()
    print(f"Wrote {ZIP_PATH.name} ({ZIP_PATH.stat().st_size / 1e6:.2f} MB, {len(names)} files)")
    for name in names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
