"""Legacy compatibility module.

The active AST implementation lives in `compiler.core.ast`.
"""

from compiler.core.ast import (
    AssignStmt as AssignNode,
    BinaryExpr as BinOpNode,
    BoolOpExpr as LogicalOpNode,
    CallExpr as FuncCallNode,
    CompareExpr as CompareNode,
    ConstantExpr,
    ExprStmt,
    FunctionDef as FuncDefNode,
    IfStmt as IfNode,
    NameExpr as VarNode,
    PrintStmt as PrintNode,
    Program as ProgramNode,
    ReturnStmt as ReturnNode,
    UnaryExpr as UnaryOpNode,
    WhileStmt as WhileNode,
)

__all__ = [
    "AssignNode",
    "BinOpNode",
    "LogicalOpNode",
    "FuncCallNode",
    "CompareNode",
    "ConstantExpr",
    "ExprStmt",
    "FuncDefNode",
    "IfNode",
    "VarNode",
    "PrintNode",
    "ProgramNode",
    "ReturnNode",
    "UnaryOpNode",
    "WhileNode",
]
