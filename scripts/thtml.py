#!/usr/bin/env python3
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from io import TextIOBase
from pathlib import Path
from typing import Any, Generator, Iterator, Mapping


def debug(msg: str) -> None:
    if bool(int(os.getenv("DEBUG", "0"))):
        print(msg, file=sys.stderr)


class Span(ABC):
    @abstractmethod
    def eval(self) -> str:
        ...

    @staticmethod
    def read_field(data: Any, field: str, required: bool = True) -> Any:
        if field == "_":
            return data
        assert isinstance(data, Mapping), f"{data} {field}"
        return data[field] if required else data.get(field)


class Text(Span):
    def __init__(self, txt: str) -> None:
        self.txt = txt

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        return self.txt

    def __repr__(self) -> str:
        return f"Text({self.txt})"


class LoadFile(Span):
    def __init__(self, span: str, base: Path) -> None:
        self.file = base / Path(span.strip())

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        with open(self.file, "r", encoding="utf-8") as f:
            return f.read()

    def __repr__(self) -> str:
        return f"LoadFile({self.file})"


class Json(Span):
    def __init__(self, span: str, base: Path) -> None:
        file, field = span.strip().rsplit(".", 1)
        self.file = base / file
        self.field = field

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        with open(self.file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return str(Span.read_field(data, self.field))

    def __repr__(self) -> str:
        return f"Json({self.file}, {self.field})"


class JsonItem(Span):
    def __init__(self, span: str) -> None:
        self.field = span.strip().lstrip(".")
        self.data: Mapping[str, Any] | None = None

    def apply(self, data: Mapping[str, Any]) -> None:
        self.data = data

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        if self.data is None:
            raise ValueError("Must call .apply() before .eval() for a JsonItem")
        return str(Span.read_field(self.data, self.field))

    def __repr__(self) -> str:
        return f"JsonItem({self.field})"


class JsonBlock(Span):
    def __init__(
        self,
        span: str,
        inner: list[Span],
        base: Path,
        required: bool = True,
        loop: bool = True,
    ) -> None:
        file, field = span.strip().rsplit(".", 1)
        self.file = base / file
        self.field = field
        self.inner = inner
        self.required = required
        self.loop = loop

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        with open(self.file, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = Span.read_field(data, self.field, required=self.required)
            if items is None:
                return ""
        txt = []
        for item in items:
            for span in self.inner:
                if self.loop and isinstance(span, (JsonItem, JsonBlockItem)):
                    span.apply(item)
                txt.append(span.eval())
            if not self.loop:
                break
        return "".join(txt)

    def __repr__(self) -> str:
        return f"JsonBlock({self.file}, {self.field}, {self.inner!r})"


class JsonBlockItem(Span):
    def __init__(
        self,
        span: str,
        inner: list[Span],
        required: bool = True,
        loop: bool = True,
    ) -> None:
        self.field = span.strip().lstrip(".")
        self.data: Mapping[str, Any] | None = None
        self.inner = inner
        self.required = required
        self.loop = loop

    def apply(self, data: Mapping[str, Any]) -> None:
        self.data = data

    def eval(self) -> str:
        debug(f"EVAL: {self!r}")
        if self.data is None:
            raise ValueError("Must call .apply() before .eval() for a JsonBlockItem")
        items = Span.read_field(self.data, self.field, required=self.required)
        if items is None:
            return ""
        txt = []
        for item in items:
            for span in self.inner:
                if self.loop and isinstance(span, (JsonItem, JsonBlockItem)):
                    span.apply(item)
                txt.append(span.eval())
            if not self.loop:
                break
        return "".join(txt)

    def __repr__(self) -> str:
        return f"JsonBlockItem({self.field}, {self.inner!r})"


class Template:
    def __init__(self, tmpl_file: Path) -> None:
        self.spans: list[Span] = []
        with open(tmpl_file, "r", encoding="utf-8") as f:
            spans = self._parse(f.read())
        self.tmpl_file = tmpl_file.resolve()
        self.spans = self._build_spans(spans)

    def _parse(self, txt: str) -> Generator[tuple[str, int, str], None, None]:
        fields = re.split(r"(<%+\w+|%>)", txt)
        inside = False
        blockdepth = 0
        kind = ""
        for f in fields:
            if f.startswith("<%%"):
                kind = f[3:].strip()
                if kind != "e":
                    blockdepth += 1
                else:
                    assert blockdepth > 0
                    blockdepth -= 1
            if f.startswith("<%"):
                if inside:
                    raise ValueError("Found nested <% %>")
                kind = f[2:].strip()
                inside = True
            elif f == "%>":
                kind = ""
                inside = False
            else:
                yield (kind, blockdepth, f)

    def _build_spans(
        self,
        txt_spans: Iterator[tuple[str, int, str]],
        curdepth: int = 0,
    ) -> list[Span]:
        spans: list[Span] = []
        try:
            while True:
                kind, blockdepth, span = next(txt_spans)
                if kind == "f":
                    spans.append(LoadFile(span, self.tmpl_file.parent))
                elif kind == "j":
                    spans.append(Json(span, self.tmpl_file.parent))
                elif kind == "ji":
                    spans.append(JsonItem(span))
                elif kind.startswith("%j"):
                    assert 0 < blockdepth and curdepth < blockdepth
                    inner = self._build_spans(txt_spans, curdepth=blockdepth)
                    if kind == "%j":
                        spans.append(JsonBlock(span, inner, self.tmpl_file.parent))
                    elif kind == "%ji":
                        spans.append(JsonBlockItem(span, inner))
                    elif kind == "%je":
                        spans.append(
                            JsonBlockItem(span, inner, required=False, loop=False)
                        )
                    elif kind == "%jo":
                        spans.append(JsonBlockItem(span, inner, required=False))
                elif kind == "":
                    spans.append(Text(span))
                elif kind == "%e":
                    pass
                else:
                    raise ValueError(f"Invalid span type: {kind}")

                if blockdepth < curdepth:
                    return spans
        except StopIteration:
            pass
        return spans

    def write(self, f: TextIOBase) -> None:
        for span in self.spans:
            f.write(span.eval())


def main(tmpl_file: Path, out: Path) -> None:
    tmpl = Template(tmpl_file)
    try:
        with open(out, "w", encoding="utf-8") as f:
            tmpl.write(f)
    except (ValueError, AssertionError) as e:
        out.unlink(missing_ok=True)
        raise e


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(f"Usage: {sys.argv[0]} THTML OUT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
