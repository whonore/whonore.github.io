#!/usr/bin/env python
import re
import sys
from abc import ABC, abstractmethod
from io import TextIOBase
from pathlib import Path
from typing import List, Tuple


class Span(ABC):
    @abstractmethod
    def eval(self) -> str:
        ...


class Text(Span):
    def __init__(self, txt: str):
        self.txt = txt

    def eval(self) -> str:
        return self.txt


class LoadFile(Span):
    def __init__(self, span: str, base: Path):
        self.file = base / Path(span.strip())

    def eval(self) -> str:
        with open(self.file, "r", encoding="utf-8") as f:
            return f.read()


class Template:
    def __init__(self, tmpl_file: str) -> None:
        self.spans: List[Span] = []
        with open(tmpl_file, "r", encoding="utf-8") as f:
            spans = self._parse(f.read())
        for kind, span in spans:
            if kind == "f":
                self.spans.append(LoadFile(span, Path(tmpl_file).resolve().parent))
            elif kind == "":
                self.spans.append(Text(span))
            else:
                raise ValueError(f"Invalid span type: {kind}")

    def _parse(self, txt: str) -> List[Tuple[str, str]]:
        spans = []
        fields = re.split(r"(<%\w|%>)", txt)
        inside = False
        kind = ""
        for f in fields:
            if f.startswith("<%"):
                if inside:
                    raise ValueError("Found nested <% %>")
                kind = f[2]
                inside = True
            elif f == "%>":
                kind = ""
                inside = False
            else:
                spans.append((kind, f))
        return spans

    def write(self, f: TextIOBase) -> None:
        for span in self.spans:
            f.write(span.eval())


def main(tmpl_file: str) -> None:
    tmpl = Template(tmpl_file)
    with open(tmpl_file.replace(".thtml", ".html"), "w", encoding="utf-8") as f:
        tmpl.write(f)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} THTML")
    main(sys.argv[1])
