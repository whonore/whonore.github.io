#!/usr/bin/env python3
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Final, Iterable, NamedTuple, Sequence, TextIO, TypeVar, cast

import shapefile  # type: ignore # pylint: disable=import-error

DIR = Path(__file__).parent
ROOT = DIR.parent

Lat = float
Lon = float
Coord = tuple[Lon, Lat]
Point = tuple[float, float]

POINT_DECIMALS = 2


def scale(
    v: float,
    from_min: float,
    from_max: float,
    to_min: float,
    to_max: float,
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


def partition(xs: Sequence[T], idxs: Iterable[int]) -> list[list[T]]:
    return [
        list(xs[start:end])
        for start, end in itertools.pairwise(itertools.chain(idxs, (None,)))
    ]


def manifests() -> list[dict[str, Any]]:
    photos = ROOT / "assets/photos"
    return [
        json.loads(manifest.read_text()) for manifest in photos.glob("*/manifest.json")
    ]


def regions() -> set[str]:
    return {data["region"] for data in manifests()}


def pointers() -> list[tuple[str, Coord, Path]]:
    return [
        (
            data["title"],
            data["coords"],
            (ROOT / "src/photos" / data["path"]).with_suffix(".html").relative_to(ROOT),
        )
        for data in manifests()
    ]


class Region(NamedTuple):
    name: str
    borders: list[list[Coord]]


class Poly(NamedTuple):
    name: str
    points: list[Coord]


class Svg:
    POINTER_RATIO: Final[float] = 1.5
    POINTER_WIDTH: float = 0.015

    def __init__(self, w: int, h: int) -> None:
        self.width = w
        self.height = h
        self.shapes: list[Poly] = []

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

    def write(self, f: TextIO) -> None:
        pwidth = self.width * self.POINTER_WIDTH
        pheight = pwidth * self.POINTER_RATIO
        ppath = " ".join(
            (
                "M 0 0",
                f"l -{pwidth / 2} -{2 * pheight / 3}",
                f"q {pwidth / 2} -{pheight / 3} {pwidth} 0",
                f"l -{pwidth / 2} {2 * pheight / 3}",
                "Z",
            )
        )
        f.write(
            "\n".join(
                (
                    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">',
                    "  <defs>",
                    f'    <path id="map-pointer" d="{ppath}" />',
                    '     <pattern id="map-stripe" patternUnits="userSpaceOnUse" width="10" height="10">',
                    '       <line x1="-10" y1="0" x2="0" y2="10" />',
                    '       <line x1="0" y1="0" x2="10" y2="10" />',
                    '       <line x1="10" y1="0" x2="20" y2="10" />',
                    "     </pattern>",
                    "  </defs>\n",
                )
            )
        )

        visited = regions()
        for shape in self.shapes:
            attrs = {
                "points": " ".join(
                    ",".join(map(Svg._float_to_str, xy)) for xy in shape.points
                ),
            }
            if shape.name in visited:
                attrs["class"] = "map-visited"
            attrstr = " ".join(f'{attr}="{val}"' for attr, val in attrs.items())
            f.write(f"  <polygon {attrstr}><title>{shape.name}</title></polygon>\n")

        for name, (lon, lat), path in pointers():
            x, y = map(
                Svg._float_to_str,
                (lon_to_x(lon, self.width), lat_to_y(lat, self.height)),
            )
            f.write(
                "\n".join(
                    (
                        f'  <a href="/{path}">',
                        f"  <title>{name}</title>",
                        f'  <use href="#map-pointer" x="{x}" y="{y}" />',
                        "  </a>\n",
                    )
                )
            )
        f.write("</svg>\n")

    @staticmethod
    def _float_to_str(x: float) -> str:
        x = round(x, POINT_DECIMALS)
        return str(int(x) if x == int(x) else x)


def parse_regions(shpf: str) -> list[Region]:
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


def main(out: str, shps: list[str], w: int, h: int) -> None:
    regs = [reg for shp in shps for reg in parse_regions(shp)]
    svg = Svg(w, h)
    for reg in regs:
        svg.add_region(reg)
    if out == "-":
        svg.write(sys.stdout)
    else:
        with open(out, "w", encoding="utf-8") as f:
            svg.write(f)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(f"Usage: {sys.argv[0]} out width height shapefiles...")
    main(sys.argv[1], sys.argv[4:], int(sys.argv[2]), int(sys.argv[3]))
