from __future__ import annotations

from dataclasses import dataclass
import ast

from compiler.frontend.source import SourceFile
from compiler.frontend.tokens import LexToken


@dataclass(frozen=True)
class ParsedModule:
    source: SourceFile
    tokens: list[LexToken]
    syntax_tree: ast.Module
