from __future__ import annotations

from compiler.core.ast import (
    AssignStmt,
    AttributeAssignStmt,
    AttributeExpr,
    BinaryExpr,
    BoolOpExpr,
    CompareExpr,
    ConstantExpr,
    ExprStmt,
    ClassDef,
    FunctionDef,
    IfStmt,
    IndexExpr,
    ListExpr,
    MethodCallExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    TupleExpr,
    UnaryExpr,
    WhileStmt,
)


class ConstantFolder:
    def optimize(self, program: Program) -> Program:
        program.body = self._optimize_statements(program.body)
        return program

    def _optimize_statements(self, statements):
        optimized = []
        for statement in statements:
            optimized.append(self._optimize_statement(statement))
            if isinstance(optimized[-1], ReturnStmt):
                break
        return optimized

    def _optimize_statement(self, statement):
        if isinstance(statement, AssignStmt):
            statement.value = self._optimize_expr(statement.value)
        elif isinstance(statement, AttributeAssignStmt):
            statement.object = self._optimize_expr(statement.object)
            statement.value = self._optimize_expr(statement.value)
        elif isinstance(statement, PrintStmt):
            statement.value = self._optimize_expr(statement.value)
        elif isinstance(statement, ExprStmt):
            statement.expr = self._optimize_expr(statement.expr)
        elif isinstance(statement, IfStmt):
            statement.condition = self._optimize_expr(statement.condition)
            statement.body = self._optimize_statements(statement.body)
            statement.orelse = self._optimize_statements(statement.orelse)
        elif isinstance(statement, WhileStmt):
            statement.condition = self._optimize_expr(statement.condition)
            statement.body = self._optimize_statements(statement.body)
        elif isinstance(statement, FunctionDef):
            statement.body = self._optimize_statements(statement.body)
        elif isinstance(statement, ClassDef):
            for method in statement.methods:
                method.body = self._optimize_statements(method.body)
        elif isinstance(statement, ReturnStmt) and statement.value is not None:
            statement.value = self._optimize_expr(statement.value)
        return statement

    def _optimize_expr(self, expr):
        if isinstance(expr, BinaryExpr):
            expr.left = self._optimize_expr(expr.left)
            expr.right = self._optimize_expr(expr.right)
            if isinstance(expr.left, ConstantExpr) and isinstance(expr.right, ConstantExpr):
                if isinstance(expr.left.value, (int, float)) and isinstance(expr.right.value, (int, float)):
                    if expr.op == "+":
                        return ConstantExpr(span=expr.span, value=expr.left.value + expr.right.value)
                    if expr.op == "-":
                        return ConstantExpr(span=expr.span, value=expr.left.value - expr.right.value)
                    if expr.op == "*":
                        return ConstantExpr(span=expr.span, value=expr.left.value * expr.right.value)
                    if expr.op == "/" and expr.right.value != 0:
                        return ConstantExpr(span=expr.span, value=expr.left.value / expr.right.value)
                    if expr.op == "%" and expr.right.value != 0:
                        return ConstantExpr(span=expr.span, value=expr.left.value % expr.right.value)
            return expr

        if isinstance(expr, UnaryExpr):
            expr.operand = self._optimize_expr(expr.operand)
            if isinstance(expr.operand, ConstantExpr):
                if expr.op == "-" and isinstance(expr.operand.value, (int, float)):
                    return ConstantExpr(span=expr.span, value=-expr.operand.value)
                if expr.op == "not":
                    return ConstantExpr(span=expr.span, value=not bool(expr.operand.value))
            return expr

        if isinstance(expr, CompareExpr):
            expr.left = self._optimize_expr(expr.left)
            expr.right = self._optimize_expr(expr.right)
            if isinstance(expr.left, ConstantExpr) and isinstance(expr.right, ConstantExpr):
                mapping = {
                    "==": expr.left.value == expr.right.value,
                    "!=": expr.left.value != expr.right.value,
                    "<": expr.left.value < expr.right.value,
                    "<=": expr.left.value <= expr.right.value,
                    ">": expr.left.value > expr.right.value,
                    ">=": expr.left.value >= expr.right.value,
                }
                return ConstantExpr(span=expr.span, value=mapping[expr.op])
            return expr

        if isinstance(expr, BoolOpExpr):
            expr.left = self._optimize_expr(expr.left)
            expr.right = self._optimize_expr(expr.right)
            if isinstance(expr.left, ConstantExpr) and isinstance(expr.right, ConstantExpr):
                left = bool(expr.left.value)
                if expr.op == "and":
                    return ConstantExpr(span=expr.span, value=left and bool(expr.right.value))
                return ConstantExpr(span=expr.span, value=left or bool(expr.right.value))
            return expr

        if isinstance(expr, ListExpr):
            expr.elements = [self._optimize_expr(element) for element in expr.elements]
            return expr

        if isinstance(expr, TupleExpr):
            expr.elements = [self._optimize_expr(element) for element in expr.elements]
            return expr

        if isinstance(expr, IndexExpr):
            expr.collection = self._optimize_expr(expr.collection)
            expr.index = self._optimize_expr(expr.index)
            return expr

        if isinstance(expr, AttributeExpr):
            expr.object = self._optimize_expr(expr.object)
            return expr

        if isinstance(expr, MethodCallExpr):
            expr.object = self._optimize_expr(expr.object)
            expr.args = [self._optimize_expr(arg) for arg in expr.args]
            return expr

        return expr
