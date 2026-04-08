"""
optimizer.py — AST Optimization Pass
======================================
Production-level optimizer for the compiler.

Features:
- Constant Folding (Arithmetic, Comparison, Logical)
- Dead Code Elimination (after return)
"""

import operator

from ast_nodes import (
    # Core nodes
    ProgramNode,
    AssignNode,
    PrintNode,
    BlockNode,

    # Expressions
    NumNode,
    StringNode,
    VarNode,
    BoolNode,

    # Operations
    BinOpNode,
    CompareNode,
    UnaryOpNode,
    LogicalOpNode,
    NotNode,

    # Control flow
    IfNode,
    WhileNode,

    # Functions
    FuncDefNode,
    ReturnNode,
    FuncCallNode,
)

# =========================
# Operator mappings
# =========================

OPS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
}

CMP_OPS = {
    '==': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
}


class Optimizer:
    """
    Performs compile-time optimizations on the AST.

    Passes:
    1. Constant Folding
    2. Dead Code Elimination
    """

    def __init__(self):
        self.folded_count = 0
        self.removed_count = 0

    # =========================
    # Entry
    # =========================

    def optimize(self, node):
        return self._visit(node)

    def _visit(self, node):
        method = f"_visit_{type(node).__name__}"
        return getattr(self, method, self._generic_visit)(node)

    def _generic_visit(self, node):
        return node

    # =========================
    # Program Structure
    # =========================

    def _visit_ProgramNode(self, node):
        node.statements = self._optimize_stmts(node.statements)
        return node

    def _visit_BlockNode(self, node):
        node.statements = self._optimize_stmts(node.statements)
        return node

    # =========================
    # Statements
    # =========================

    def _visit_AssignNode(self, node):
        node.value = self._visit(node.value)
        return node

    def _visit_PrintNode(self, node):
        node.expr = self._visit(node.expr)
        return node

    def _visit_ReturnNode(self, node):
        node.expr = self._visit(node.expr)
        return node

    def _visit_FuncDefNode(self, node):
        node.body = self._visit(node.body)
        return node

    def _visit_FuncCallNode(self, node):
        node.args = [self._visit(arg) for arg in node.args]
        return node

    # =========================
    # Control Flow
    # =========================

    def _visit_IfNode(self, node):
        node.condition = self._visit(node.condition)
        node.if_body = self._visit(node.if_body)

        if node.else_body:
            node.else_body = self._visit(node.else_body)

        return node

    def _visit_WhileNode(self, node):
        node.condition = self._visit(node.condition)
        node.body = self._visit(node.body)
        return node

    # =========================
    # Expressions
    # =========================

    def _visit_BinOpNode(self, node):
        node.left = self._visit(node.left)
        node.right = self._visit(node.right)

        if isinstance(node.left, NumNode) and isinstance(node.right, NumNode):
            if node.op in OPS:
                if node.op == "/" and node.right.value == 0:
                    return node  # avoid division by zero

                result = OPS[node.op](node.left.value, node.right.value)

                # Preserve int where possible
                if (
                    isinstance(node.left.value, int)
                    and isinstance(node.right.value, int)
                    and node.op != "/"
                ):
                    result = int(result)

                self.folded_count += 1
                return NumNode(result)

        return node

    def _visit_CompareNode(self, node):
        node.left = self._visit(node.left)
        node.right = self._visit(node.right)

        if isinstance(node.left, NumNode) and isinstance(node.right, NumNode):
            if node.op in CMP_OPS:
                result = CMP_OPS[node.op](node.left.value, node.right.value)
                self.folded_count += 1
                return BoolNode(result)

        return node

    def _visit_UnaryOpNode(self, node):
        node.operand = self._visit(node.operand)

        if isinstance(node.operand, NumNode) and node.op == "-":
            self.folded_count += 1
            return NumNode(-node.operand.value)

        return node

    # =========================
    # 🔥 LOGICAL OPTIMIZATION
    # =========================

    def _visit_BoolNode(self, node):
        return node

    def _visit_LogicalOpNode(self, node):
        node.left = self._visit(node.left)
        node.right = self._visit(node.right)

        if isinstance(node.left, (BoolNode, NumNode)) and isinstance(node.right, (BoolNode, NumNode)):
            l = bool(node.left.value)
            r = bool(node.right.value)

            result = (l and r) if node.op == "and" else (l or r)

            self.folded_count += 1
            return BoolNode(result)

        return node

    def _visit_NotNode(self, node):
        node.operand = self._visit(node.operand)

        if isinstance(node.operand, (BoolNode, NumNode)):
            self.folded_count += 1
            return BoolNode(not bool(node.operand.value))

        return node

    # =========================
    # Literals
    # =========================

    def _visit_NumNode(self, node):
        return node

    def _visit_StringNode(self, node):
        return node

    def _visit_VarNode(self, node):
        return node

    # =========================
    # Dead Code Elimination
    # =========================

    def _optimize_stmts(self, stmts):
        result = []

        for stmt in stmts:
            optimized = self._visit(stmt)
            result.append(optimized)

            if isinstance(optimized, ReturnNode):
                removed = len(stmts) - len(result)
                if removed > 0:
                    self.removed_count += removed
                break

        return result