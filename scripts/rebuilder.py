#!/usr/bin/env python3
import subprocess
import sys
import time
from collections import defaultdict as ddict
from pathlib import Path
from typing import DefaultDict, Iterable

from pathspec import PathSpec  # type: ignore

DIR = Path(__file__).parent
ROOT = DIR.parent

IGNORE = [".git", ".github"]
POLL_RATE_MS = 1000


def gitignore(g: Path) -> PathSpec:
    ignore = PathSpec.from_lines("gitwildmatch", IGNORE)
    with open(g, "r", encoding="utf-8") as f:
        return ignore + PathSpec.from_lines("gitwildmatch", f)


def collect_files(fs: Iterable[str | Path], ignore: PathSpec) -> list[Path]:
    ps = []
    for p in (Path(f).resolve().relative_to(ROOT) for f in fs):
        if ignore.match_file(p):
            continue
        if p.is_dir():
            ps += collect_files(p.iterdir(), ignore)
        else:
            ps.append(p)
    return ps


def rebuild(replace: bool = True) -> None:
    print("BUILDING")
    try:
        if replace:
            result = Path(ROOT / "result")
            if result.exists():
                result_real = result.resolve()
                result.unlink()
                subprocess.run(("nix", "store", "delete", result_real), check=True)
        subprocess.run(("nix", "build"), check=True)
    except subprocess.CalledProcessError:
        print("BUILDING FAILED")


def watch(*args: str) -> None:
    ignore = gitignore(ROOT / ".gitignore")
    mtimes: DefaultDict[Path, float] = ddict(float)
    while True:
        build = False
        for f in collect_files(args, ignore):
            mtime = f.stat().st_mtime
            if mtime > mtimes[f]:
                print(f"CHANGED: {f}")
                mtimes[f] = mtime
                build = True
        if build:
            rebuild()
        time.sleep(POLL_RATE_MS / 1000)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} files/dirs...")
    try:
        watch(*sys.argv[1:])
    except KeyboardInterrupt:
        pass
