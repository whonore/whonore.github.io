#!/usr/bin/env python
import itertools
import math
import sys
from io import TextIOBase
from pathlib import Path
from typing import (
    Any,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)

import shapefile  # type: ignore # pylint: disable=import-error

DIR = Path(__file__).parent
ROOT = DIR.parent

Lat = float
Lon = float
Coord = Tuple[Lon, Lat]
Point = Tuple[float, float]


def scale(
    v: float, from_min: float, from_max: float, to_min: float, to_max: float
) -> float:
    assert (
        from_min <= v <= from_max
        or math.isclose(v, from_min)
        or math.isclose(v, from_max)
    )
    v = min(from_max, max(from_min, v))
    v = v - from_min  # [0 .. from_max - from_min]
    v = v / (from_max - from_min)  # [0 .. 1]
    v = v * (to_max - to_min)  # [0 .. to_max - to_min]
    v = v + to_min  # [to_min .. to_max]
    return v


def lon_to_x(lon: float, w: int) -> float:
    return scale(lon, -180, 180, 0, w)


def lat_to_y(lat: float, h: int) -> float:
    return scale(-lat, -90, 90, 0, h)


T = TypeVar("T")


def partition(xs: Sequence[T], idxs: Iterable[int]) -> List[List[T]]:
    return [
        list(xs[start:end])
        for start, end in itertools.pairwise(itertools.chain(idxs, (None,)))
    ]


def photo_link(name: str) -> Optional[Path]:
    src = ROOT / "src/photos"
    canonical = name.lower().replace(" ", "_")
    photos = Path(src / canonical).with_suffix(".html").relative_to(ROOT)
    return photos if photos.exists() else None


class Region(NamedTuple):
    name: str
    borders: List[List[Coord]]


class Poly(NamedTuple):
    name: str
    points: List[Coord]


class Svg:
    def __init__(self, w: int, h: int) -> None:
        self.width = w
        self.height = h
        self.shapes: List[Poly] = []

    def add_region(self, reg: Region) -> None:
        shapes = [
            Poly(
                reg.name,
                [
                    (lon_to_x(lon, self.width), lat_to_y(lat, self.height))
                    for lon, lat in border
                ],
            )
            for border in reg.borders
        ]
        self.shapes += shapes

    def write(self, f: TextIOBase) -> None:
        f.write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">\n'
        )
        for shape in self.shapes:
            attrs = {
                "points": " ".join(",".join(map(str, xy)) for xy in shape.points),
            }
            photos = photo_link(shape.name)
            if photos is not None:
                attrs["class"] = "active"
                f.write(f'  <a xlink:href="{photos.relative_to("src")}">')
            attrstr = " ".join(f'{attr}="{val}"' for attr, val in attrs.items())
            f.write(f"  <polygon {attrstr}><title>{shape.name}</title></polygon>\n")
            if photos is not None:
                f.write("  </a>")
        f.write("</svg>\n")


def parse_regions(shpf: str) -> List[Region]:
    def name(rec: Any) -> str:
        keys = ("name_en", "NAME_EN")
        for key in keys:
            try:
                return cast(str, rec[key])
            except IndexError:
                pass
        raise ValueError("Cannot find name")

    with shapefile.Reader(shpf) as shp:
        return [
            Region(name(rec.record), partition(rec.shape.points, rec.shape.parts))
            for rec in shp.shapeRecords()
        ]


def main(shps: List[str], w: int, h: int) -> None:
    regs = [reg for shp in shps for reg in parse_regions(shp)]
    svg = Svg(w, h)
    for reg in regs:
        svg.add_region(reg)
    with open(ROOT / "assets/generated/map.svg", "w", encoding="utf-8") as f:
        svg.write(f)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(f"Usage: {sys.argv[0]} width height shapefiles...")
    main(sys.argv[3:], int(sys.argv[1]), int(sys.argv[2]))
