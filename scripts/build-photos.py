#!/usr/bin/env python3
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = DIR.parent


def subst(tmpl: Path, manifest: Path) -> None:
    txt = tmpl.read_text(encoding="utf-8")
    place = manifest.parent.name
    out = ROOT / f"src/photos/{place}.thtml"
    path = f"../../{manifest.relative_to(ROOT)}"
    out.write_text(txt.replace("$MANIFEST", path), encoding="utf-8")


def main(place: str) -> None:
    tmpl = ROOT / "src/photos/_photos.thtml.tmpl"
    manifest = (ROOT / f"assets/photos/{place}/manifest.json").resolve()
    subst(tmpl, manifest)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} PLACE")
    main(sys.argv[1])
