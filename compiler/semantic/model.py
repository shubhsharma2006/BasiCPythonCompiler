from __future__ import annotations

from dataclasses import dataclass, field

from compiler.core.ast import CallExpr
from compiler.core.types import FunctionType, ValueType


class Scope:
    def __init__(self, parent: Scope | None = None):
        self.parent = parent
        self.values: dict[str, ValueType] = {}

    def define(self, name: str, value_type: ValueType) -> None:
        self.values[name] = value_type

    def lookup(self, name: str) -> ValueType | None:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


@dataclass
class SymbolTable:
    global_scope: Scope = field(default_factory=Scope)
    functions: dict[str, FunctionType] = field(default_factory=dict)


@dataclass
class SemanticModel:
    globals: dict[str, ValueType]
    functions: dict[str, FunctionType]
    expr_types: dict[int, ValueType]

    def expr_type(self, expr) -> ValueType:
        if isinstance(expr, CallExpr) and expr.func_name in self.functions:
            value_type = self.expr_types.get(id(expr), ValueType.UNKNOWN)
            if value_type == ValueType.UNKNOWN:
                return self.functions[expr.func_name].return_type
            return value_type
        return self.expr_types.get(id(expr), ValueType.UNKNOWN)
