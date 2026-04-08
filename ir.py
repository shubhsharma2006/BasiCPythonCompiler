"""
ir.py — Intermediate Representation Generator (Production)
=========================================================
Generates a flat list of IR instructions including structured markers
for control flow (IF_BEGIN, IF_END, WHILE_BEGIN, etc.)

Supports:
- Arithmetic
- Comparison
- Logical operations (and, or, not)
- Functions
- Control flow
"""

from ast_nodes import (
    ProgramNode, AssignNode, PrintNode, BlockNode,
    NumNode, StringNode, VarNode, BoolNode,
    BinOpNode, CompareNode, UnaryOpNode,
    LogicalOpNode, NotNode,
    IfNode, WhileNode,
    FuncDefNode, ReturnNode, FuncCallNode,
)


# =========================
# IR Instruction
# =========================

class IRInstruction:
    def __init__(self, op, result=None, arg1=None, arg2=None, operator=None, extra=None):
        self.op = op
        self.result = result
        self.arg1 = arg1
        self.arg2 = arg2
        self.operator = operator
        self.extra = extra

    def __repr__(self):
        if self.op == 'binop':
            return f"{self.result} = {self.arg1} {self.operator} {self.arg2}"
        elif self.op == 'compare':
            return f"{self.result} = {self.arg1} {self.operator} {self.arg2}"
        elif self.op == 'assign':
            return f"{self.result} = {self.arg1}"
        elif self.op == 'print':
            return f"PRINT {self.arg1}"
        elif self.op == 'print_str':
            return f'PRINT_STR "{self.arg1}"'
        elif self.op == 'if_begin':
            return f"IF {self.arg1} {{"
        elif self.op == 'else':
            return "} ELSE {"
        elif self.op == 'if_end':
            return "}"
        elif self.op == 'while_begin':
            return "WHILE {"
        elif self.op == 'while_cond':
            return f"  BREAK_IF_FALSE {self.arg1}"
        elif self.op == 'while_end':
            return "} END_WHILE"
        elif self.op == 'func_begin':
            params = ", ".join(self.extra or [])
            return f"FUNC {self.arg1}({params}) {{"
        elif self.op == 'func_end':
            return f"}} END_FUNC"
        elif self.op == 'return':
            return f"RETURN {self.arg1}"
        elif self.op == 'param':
            return f"PARAM {self.arg1}"
        elif self.op == 'call':
            return f"{self.result} = CALL {self.arg1}({self.arg2} args)"
        elif self.op == 'unary':
            return f"{self.result} = {self.operator}{self.arg1}"
        return f"?? {self.op}"


# =========================
# IR Generator
# =========================

class IRGenerator:
    def __init__(self):
        self._temp_count = 0
        self.instructions = []

    def _new_temp(self):
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _emit(self, op, **kw):
        self.instructions.append(IRInstruction(op, **kw))

    def generate(self, node):
        self._visit(node)
        return self.instructions

    def _visit(self, node):
        method = f'_visit_{type(node).__name__}'
        visitor = getattr(self, method, None)
        if not visitor:
            raise NotImplementedError(f"IR: no visitor for {type(node).__name__}")
        return visitor(node)

    # =========================
    # Statements
    # =========================

    def _visit_ProgramNode(self, node):
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_AssignNode(self, node):
        rhs = self._visit(node.value)
        if rhs != node.name:
            self._emit('assign', result=node.name, arg1=rhs)

    def _visit_PrintNode(self, node):
        if isinstance(node.expr, StringNode):
            self._emit('print_str', arg1=node.expr.value)
        else:
            val = self._visit(node.expr)
            self._emit('print', arg1=val)

    def _visit_IfNode(self, node):
        cond = self._visit(node.condition)
        self._emit('if_begin', arg1=cond)
        self._visit(node.if_body)

        if node.else_body:
            self._emit('else')
            self._visit(node.else_body)

        self._emit('if_end')

    def _visit_WhileNode(self, node):
        self._emit('while_begin')
        cond = self._visit(node.condition)
        self._emit('while_cond', arg1=cond)
        self._visit(node.body)
        self._emit('while_end')

    def _visit_BlockNode(self, node):
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_FuncDefNode(self, node):
        self._emit('func_begin', arg1=node.name, extra=node.params)
        self._visit(node.body)
        self._emit('func_end', arg1=node.name)

    def _visit_ReturnNode(self, node):
        val = self._visit(node.expr)
        self._emit('return', arg1=val)

    # =========================
    # Expressions
    # =========================

    def _visit_BinOpNode(self, node):
        left = self._visit(node.left)
        right = self._visit(node.right)

        t = self._new_temp()
        self._emit('binop', result=t, arg1=left, operator=node.op, arg2=right)
        return t

    def _visit_CompareNode(self, node):
        left = self._visit(node.left)
        right = self._visit(node.right)

        t = self._new_temp()
        self._emit('compare', result=t, arg1=left, operator=node.op, arg2=right)
        return t

    def _visit_UnaryOpNode(self, node):
        operand = self._visit(node.operand)

        t = self._new_temp()
        self._emit('unary', result=t, arg1=operand, operator=node.op)
        return t

    # =========================
    # 🔥 Logical Expressions
    # =========================

    def _visit_BoolNode(self, node):
        return '1' if node.value else '0'

    def _visit_LogicalOpNode(self, node):
        left = self._visit(node.left)
        right = self._visit(node.right)

        t = self._new_temp()
        op = '&&' if node.op == 'and' else '||'

        self._emit('binop', result=t, arg1=left, operator=op, arg2=right)
        return t

    def _visit_NotNode(self, node):
        operand = self._visit(node.operand)

        t = self._new_temp()
        self._emit('unary', result=t, arg1=operand, operator='!')
        return t

    # =========================
    # Literals
    # =========================

    def _visit_NumNode(self, node):
        return str(node.value)

    def _visit_StringNode(self, node):
        return node.value

    def _visit_VarNode(self, node):
        return node.name

    def _visit_FuncCallNode(self, node):
        args = [self._visit(a) for a in node.args]

        for a in args:
            self._emit('param', arg1=a)

        t = self._new_temp()
        self._emit('call', result=t, arg1=node.name, arg2=len(args))
        return t