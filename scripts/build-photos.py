#!/usr/bin/env python3
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = DIR.parent


def subst(tmpl: Path, manifest: Path, out: Path) -> None:
    txt = tmpl.read_text(encoding="utf-8")
    place = manifest.parent.name
    out = out / f"src/photos/{place}.thtml"
    out.write_text(txt.replace("$MANIFEST", str(manifest)), encoding="utf-8")


def main(place: str, out: Path) -> None:
    tmpl = ROOT / "src/photos/_photos.thtml.tmpl"
    manifest = (ROOT / f"assets/photos/{place}/manifest.json").resolve()
    subst(tmpl, manifest, out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(f"Usage: {sys.argv[0]} PLACE BUILD_DIR")
    main(sys.argv[1], Path(sys.argv[2]).resolve())
