from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFile:
    filename: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()
