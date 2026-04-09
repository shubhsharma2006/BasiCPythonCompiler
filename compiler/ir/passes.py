from __future__ import annotations

from dataclasses import dataclass

from compiler.core.types import ValueType
from compiler.ir.analysis import reachable_block_names, rebuild_edges, reverse_post_order
from compiler.ir.cfg import (
    Assign,
    BinaryOp,
    BranchTerminator,
    CFGFunction,
    CFGModule,
    JumpTerminator,
    LoadConst,
    Print,
    ReturnTerminator,
    UnaryOp,
)


UNKNOWN = object()


@dataclass(frozen=True)
class ConstantValue:
    value: object
    value_type: ValueType


class CFGConstantPropagation:
    def optimize(self, module: CFGModule) -> CFGModule:
        self._optimize_function(module.main)
        for function in module.functions:
            self._optimize_function(function)
        return module

    def _optimize_function(self, function: CFGFunction) -> None:
        rebuild_edges(function)
        order = reverse_post_order(function)
        if not order:
            return

        in_states: dict[str, dict[str, object]] = {name: {} for name in order}
        out_states: dict[str, dict[str, object]] = {name: {} for name in order}

        changed = True
        while changed:
            changed = False
            for block_name in order:
                block = next(block for block in function.blocks if block.name == block_name)
                incoming = self._merge_predecessors(function, block_name, out_states)
                state = dict(incoming)
                rewritten = []
                for instruction in block.instructions:
                    new_instruction = self._rewrite_instruction(instruction, state)
                    rewritten.append(new_instruction)
                    self._transfer(new_instruction, state)
                block.instructions = rewritten

                new_terminator = self._rewrite_terminator(block.terminator, state)
                block.terminator = new_terminator
                if incoming != in_states[block_name] or state != out_states[block_name]:
                    in_states[block_name] = incoming
                    out_states[block_name] = state
                    changed = True

        rebuild_edges(function)
        reachable = reachable_block_names(function)
        function.blocks = [block for block in function.blocks if block.name in reachable]
        rebuild_edges(function)

    def _merge_predecessors(self, function: CFGFunction, block_name: str, out_states: dict[str, dict[str, object]]) -> dict[str, object]:
        block = next(block for block in function.blocks if block.name == block_name)
        if block.name == function.entry_block:
            return {}
        predecessors = [out_states[pred] for pred in block.predecessors if pred in out_states]
        if not predecessors:
            return {}

        merged: dict[str, object] = {}
        keys = set().union(*(state.keys() for state in predecessors))
        for key in keys:
            values = [state.get(key, UNKNOWN) for state in predecessors]
            first = values[0]
            if all(self._same_constant(first, value) for value in values[1:]):
                merged[key] = first
            else:
                merged[key] = UNKNOWN
        return merged

    def _rewrite_instruction(self, instruction, state: dict[str, object]):
        if isinstance(instruction, Assign):
            source = self._const_for_name(instruction.source, state)
            if isinstance(source, ConstantValue):
                return LoadConst(instruction.target, source.value, source.value_type)
            return instruction

        if isinstance(instruction, UnaryOp):
            operand = self._const_for_name(instruction.operand, state)
            if isinstance(operand, ConstantValue):
                if instruction.op == "-":
                    return LoadConst(instruction.target, -operand.value, instruction.value_type)
                if instruction.op == "!":
                    return LoadConst(instruction.target, not bool(operand.value), ValueType.BOOL)
            return instruction

        if isinstance(instruction, BinaryOp):
            left = self._const_for_name(instruction.left, state)
            right = self._const_for_name(instruction.right, state)
            if isinstance(left, ConstantValue) and isinstance(right, ConstantValue):
                folded = self._fold_binary(instruction.op, left.value, right.value, instruction.value_type)
                if folded is not None:
                    return LoadConst(instruction.target, folded, instruction.value_type)
            return instruction

        return instruction

    def _transfer(self, instruction, state: dict[str, object]) -> None:
        if isinstance(instruction, LoadConst):
            state[instruction.target] = ConstantValue(instruction.value, instruction.value_type)
        elif isinstance(instruction, Assign):
            state[instruction.target] = state.get(instruction.source, UNKNOWN)
        elif isinstance(instruction, (BinaryOp, UnaryOp)):
            state[instruction.target] = UNKNOWN
        elif hasattr(instruction, "target") and getattr(instruction, "target", None):
            state[instruction.target] = UNKNOWN

    def _rewrite_terminator(self, terminator, state: dict[str, object]):
        if isinstance(terminator, BranchTerminator):
            condition = self._const_for_name(terminator.condition, state)
            if isinstance(condition, ConstantValue):
                target = terminator.true_target if bool(condition.value) else terminator.false_target
                return JumpTerminator(target)
        return terminator

    @staticmethod
    def _const_for_name(name: str, state: dict[str, object]) -> object:
        return state.get(name, UNKNOWN)

    @staticmethod
    def _same_constant(left: object, right: object) -> bool:
        if left is UNKNOWN or right is UNKNOWN:
            return left is right
        return isinstance(left, ConstantValue) and isinstance(right, ConstantValue) and left == right

    @staticmethod
    def _fold_binary(op: str, left: object, right: object, value_type: ValueType):
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/" and right != 0:
            return left / right
        if op == "%" and right != 0:
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        return None
