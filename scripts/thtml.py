#!/usr/bin/env python3
import json
import re
import sys
from abc import ABC, abstractmethod
from io import TextIOBase
from pathlib import Path
from typing import Any, Generator, Iterator, Mapping


class Span(ABC):
    @abstractmethod
    def eval(self) -> str:
        ...


class Text(Span):
    def __init__(self, txt: str) -> None:
        self.txt = txt

    def eval(self) -> str:
        return self.txt


class LoadFile(Span):
    def __init__(self, span: str, base: Path) -> None:
        self.file = base / Path(span.strip())

    def eval(self) -> str:
        with open(self.file, "r", encoding="utf-8") as f:
            return f.read()


class Json(Span):
    def __init__(self, span: str, base: Path) -> None:
        file, field = span.strip().rsplit(".", 1)
        self.file = base / file
        self.field = field

    def eval(self) -> str:
        with open(self.file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[self.field]  # type: ignore


class JsonItem(Span):
    def __init__(self, span: str) -> None:
        self.field = span.strip().lstrip(".")
        self.data: Mapping[str, Any] | None = None

    def apply(self, data: Mapping[str, Any]) -> None:
        self.data = data

    def eval(self) -> str:
        if self.data is None:
            raise ValueError("Must call .apply() before .eval() for a JsonItem")
        return self.data[self.field]  # type: ignore


class JsonBlock(Span):
    def __init__(self, span: str, inner: list[Span], base: Path) -> None:
        file, field = span.strip().rsplit(".", 1)
        self.file = base / file
        self.field = field
        self.inner = inner

    def eval(self) -> str:
        with open(self.file, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data[self.field]
        txt = []
        for item in items:
            for span in self.inner:
                if isinstance(span, JsonItem):
                    span.apply(item)
                txt.append(span.eval())
        return "".join(txt)


class Template:
    def __init__(self, tmpl_file: Path) -> None:
        self.spans: list[Span] = []
        with open(tmpl_file, "r", encoding="utf-8") as f:
            spans = self._parse(f.read())
        self.tmpl_file = tmpl_file.resolve()
        self.spans = self._build_spans(spans)

    def _parse(self, txt: str) -> Generator[tuple[str, bool, str], None, None]:
        fields = re.split(r"(<%+\w+|%>)", txt)
        inside = False
        block = False
        kind = ""
        for f in fields:
            if f.startswith("<%%"):
                kind = f[3:].strip()
                block = kind != "e"
            if f.startswith("<%"):
                if inside:
                    raise ValueError("Found nested <% %>")
                kind = f[2:].strip()
                inside = True
            elif f == "%>":
                kind = ""
                inside = False
            else:
                yield (kind, block, f)

    def _build_spans(
        self,
        txt_spans: Iterator[tuple[str, bool, str]],
        in_block: bool = False,
    ) -> list[Span]:
        spans: list[Span] = []
        try:
            while True:
                kind, block, span = next(txt_spans)
                if kind == "f":
                    spans.append(LoadFile(span, self.tmpl_file.parent))
                elif kind == "j":
                    spans.append(Json(span, self.tmpl_file.parent))
                elif kind == "ji":
                    spans.append(JsonItem(span))
                elif kind == "%j":
                    assert block
                    inner = self._build_spans(txt_spans, in_block=True)
                    spans.append(JsonBlock(span, inner, self.tmpl_file.parent))
                elif kind == "":
                    spans.append(Text(span))
                elif kind == "%e":
                    pass
                else:
                    raise ValueError(f"Invalid span type: {kind}")

                if in_block and not block:
                    return spans
        except StopIteration:
            pass
        return spans

    def write(self, f: TextIOBase) -> None:
        for span in self.spans:
            f.write(span.eval())


def main(tmpl_file: Path) -> None:
    tmpl = Template(tmpl_file)
    with open(tmpl_file.with_suffix(".html"), "w", encoding="utf-8") as f:
        tmpl.write(f)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} THTML")
    main(Path(sys.argv[1]))
