from __future__ import annotations

from dataclasses import dataclass

from compiler.frontend.source import SourceFile


@dataclass(frozen=True)
class LexToken:
    kind: str
    text: str
    line: int
    column: int
    end_line: int
    end_column: int
    exact_kind: str


@dataclass(frozen=True)
class LexedSource:
    source: SourceFile
    tokens: list[LexToken]
