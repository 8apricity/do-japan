"""Build the static site and restore the original video without re-encoding.

Uses Python's standard library only. Run from any working directory.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(output: Path) -> None:
    manifest = json.loads((ROOT / "video" / "manifest.json").read_text(encoding="utf-8"))
    if manifest["filename"] != "do-japan.mp4":
        raise ValueError("The download filename must be do-japan.mp4")
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(ROOT / "video") or output.is_relative_to(ROOT / "site"):
        raise ValueError("Choose a separate build directory, such as _site")
    output.mkdir(parents=True, exist_ok=True)

    target = output / "do-japan.mp4"
    temporary = output / "do-japan.mp4.partial"
    original_hash = hashlib.sha256()
    total_bytes = 0

    try:
        with temporary.open("wb") as assembled:
            for part in manifest["parts"]:
                name = part["file"]
                if Path(name).name != name or "/" in name or "\\" in name:
                    raise ValueError(f"Invalid part name: {name}")
                part_hash = hashlib.sha256()
                part_bytes = 0
                with (ROOT / "video" / name).open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        assembled.write(chunk)
                        original_hash.update(chunk)
                        part_hash.update(chunk)
                        part_bytes += len(chunk)
                if part_bytes != part["bytes"] or part_hash.hexdigest() != part["sha256"]:
                    raise ValueError(f"Video part is incomplete or changed: {name}")
                total_bytes += part_bytes

        if total_bytes != manifest["bytes"] or original_hash.hexdigest() != manifest["sha256"]:
            raise ValueError("Restored video does not match the original file")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    for item in (ROOT / "site").iterdir():
        destination = output / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)

    print(f"Built site: {output}")
    print(f"Video: {total_bytes:,} bytes (original bytes, no re-encoding)")
    print(f"SHA-256: {original_hash.hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.output.resolve())
