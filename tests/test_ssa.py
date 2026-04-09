import os
import tempfile
import unittest

from compiler import compile_source
from compiler.core.types import ValueType
from compiler.ir import (
    Assign,
    BasicBlock,
    BinaryOp,
    BranchTerminator,
    CFGFunction,
    CFGModule,
    JumpTerminator,
    LoadConst,
    Phi,
    ReturnTerminator,
    SSAConstantPropagation,
    SSAValuePropagation,
    build_use_def_map,
    dominance_frontiers,
    immediate_dominators,
)


class SSATests(unittest.TestCase):
    def compile_program(self, source: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = compile_source(source, filename="ssa_test.py", output=os.path.join(temp_dir, "program.c"))
            self.assertTrue(result.success, result.errors.render())
            return result

    def test_phi_inserted_at_merge(self):
        result = self.compile_program(
            "def choose(flag):\n"
            "    if flag:\n"
            "        y = 1\n"
            "    else:\n"
            "        y = 2\n"
            "    return y\n\n"
            "print(choose(True))\n"
        )
        function = next(func for func in result.ssa.functions if func.name == "choose")
        phi_nodes = [phi for block in function.blocks for phi in block.phis if phi.variable == "y"]
        self.assertTrue(phi_nodes)
        self.assertEqual(len(phi_nodes[0].inputs), 2)

    def test_ssa_renames_values(self):
        result = self.compile_program(
            "def choose(flag):\n"
            "    if flag:\n"
            "        x = 1\n"
            "    else:\n"
            "        x = 2\n"
            "    return x\n\n"
            "print(choose(True))\n"
        )
        function = next(func for func in result.ssa.functions if func.name == "choose")
        phi_targets = [phi.target for block in function.blocks for phi in block.phis if phi.variable == "x"]
        self.assertTrue(any(name.startswith("x.") for name in phi_targets))

    def test_frontier_and_idom_helpers(self):
        result = self.compile_program(
            "def choose(flag):\n"
            "    if flag:\n"
            "        value = 1\n"
            "    else:\n"
            "        value = 2\n"
            "    return value\n\n"
            "print(choose(True))\n"
        )
        function = next(func for func in result.ir.functions if func.name == "choose")
        frontiers = dominance_frontiers(function)
        idoms = immediate_dominators(function)
        self.assertIn(function.entry_block, idoms)
        self.assertTrue(any(frontiers.values()))

    def test_ssa_dead_defs_are_removed(self):
        result = self.compile_program(
            "def work(x):\n"
            "    y = x + 1\n"
            "    z = x + 2\n"
            "    return y\n\n"
            "print(work(5))\n"
        )
        function = next(func for func in result.ssa.functions if func.name == "work")
        defs = build_use_def_map(function)
        self.assertTrue(any(name.startswith("_t") for name in defs))
        self.assertFalse(any(name.startswith("z.") for name in defs))

    def test_ssa_copy_propagation_collapses_copy_chain(self):
        result = self.compile_program(
            "def alias(x):\n"
            "    y = x\n"
            "    z = y\n"
            "    return z\n\n"
            "print(alias(5))\n"
        )
        function = next(func for func in result.ssa.functions if func.name == "alias")
        defs = build_use_def_map(function)
        self.assertFalse(any(name.startswith("y.") for name in defs))
        self.assertFalse(any(name.startswith("z.") for name in defs))

    def test_ssa_constant_propagation_lowers_constant_phi(self):
        function = CFGFunction(name="f", params=[("flag", ValueType.BOOL)], return_type=ValueType.INT, entry_block="entry")
        entry = BasicBlock(name="entry", terminator=BranchTerminator("flag", "left", "right"))
        left = BasicBlock(
            name="left",
            instructions=[LoadConst("x.1", 1, ValueType.INT), LoadConst("two", 2, ValueType.INT)],
            terminator=JumpTerminator("join"),
        )
        right = BasicBlock(
            name="right",
            instructions=[LoadConst("x.2", 1, ValueType.INT)],
            terminator=JumpTerminator("join"),
        )
        join = BasicBlock(
            name="join",
            phis=[Phi(target="x.3", variable="x", inputs={"left": "x.1", "right": "x.2"}, value_type=ValueType.INT)],
            instructions=[BinaryOp(target="y.1", op="+", left="x.3", right="two", value_type=ValueType.INT)],
            terminator=ReturnTerminator("y.1"),
        )
        function.blocks = [entry, left, right, join]
        module = CFGModule(globals={}, functions=[], main=function, function_types={})

        SSAConstantPropagation().optimize(module)

        join_block = next(block for block in module.main.blocks if block.name == "join")
        self.assertFalse(join_block.phis)
        self.assertIsInstance(join_block.instructions[0], LoadConst)
        self.assertEqual(join_block.instructions[0].target, "x.3")
        self.assertEqual(join_block.instructions[0].value, 1)
        self.assertIsInstance(join_block.instructions[1], LoadConst)
        self.assertEqual(join_block.instructions[1].target, "y.1")
        self.assertEqual(join_block.instructions[1].value, 3)

    def test_ssa_constant_propagation_prunes_constant_branch(self):
        function = CFGFunction(name="f", params=[], return_type=ValueType.INT, entry_block="entry")
        entry = BasicBlock(
            name="entry",
            instructions=[LoadConst("cond.1", True, ValueType.BOOL)],
            terminator=BranchTerminator("cond.1", "live", "dead"),
        )
        live = BasicBlock(name="live", instructions=[LoadConst("x.1", 1, ValueType.INT)], terminator=ReturnTerminator("x.1"))
        dead = BasicBlock(name="dead", instructions=[LoadConst("x.2", 2, ValueType.INT)], terminator=ReturnTerminator("x.2"))
        function.blocks = [entry, live, dead]
        module = CFGModule(globals={}, functions=[], main=function, function_types={})

        SSAConstantPropagation().optimize(module)

        optimized_entry = next(block for block in module.main.blocks if block.name == "entry")
        self.assertIsInstance(optimized_entry.terminator, JumpTerminator)
        self.assertEqual(optimized_entry.terminator.target, "live")
        self.assertEqual({block.name for block in module.main.blocks}, {"entry", "live"})

    def test_ssa_value_propagation_rewrites_algebraic_identities(self):
        function = CFGFunction(name="f", params=[("x.1", ValueType.INT)], return_type=ValueType.INT, entry_block="entry")
        entry = BasicBlock(
            name="entry",
            instructions=[
                LoadConst("zero", 0, ValueType.INT),
                LoadConst("one", 1, ValueType.INT),
                BinaryOp(target="y.1", op="+", left="x.1", right="zero", value_type=ValueType.INT),
                BinaryOp(target="z.1", op="*", left="y.1", right="one", value_type=ValueType.INT),
            ],
            terminator=ReturnTerminator("z.1"),
        )
        function.blocks = [entry]
        module = CFGModule(globals={}, functions=[], main=function, function_types={})

        SSAValuePropagation().optimize(module)

        self.assertIsInstance(entry.instructions[2], Assign)
        self.assertEqual(entry.instructions[2].source, "x.1")
        self.assertIsInstance(entry.instructions[3], Assign)
        self.assertEqual(entry.instructions[3].source, "y.1")


if __name__ == "__main__":
    unittest.main()
