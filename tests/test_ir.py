import os
import tempfile
import unittest

from compiler import compile_source
from compiler.ir import BranchTerminator, JumpTerminator, compute_dominators, reverse_post_order


class IRTests(unittest.TestCase):
    def compile_program(self, source: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = compile_source(source, filename="ir_test.py", output=os.path.join(temp_dir, "program.c"))
            self.assertTrue(result.success, result.errors.render())
            return result

    def test_reverse_post_order_starts_at_entry(self):
        result = self.compile_program(
            "x = 1\n"
            "if x:\n"
            "    print(1)\n"
            "else:\n"
            "    print(2)\n"
        )
        order = reverse_post_order(result.ir.main)
        self.assertTrue(order)
        self.assertEqual(order[0], result.ir.main.entry_block)

    def test_dominators_include_entry(self):
        result = self.compile_program(
            "x = 1\n"
            "if x:\n"
            "    print(1)\n"
            "print(3)\n"
        )
        dominators = compute_dominators(result.ir.main)
        entry = result.ir.main.entry_block
        for block_name, doms in dominators.items():
            self.assertIn(entry, doms)
            self.assertIn(block_name, doms)

    def test_constant_propagation_simplifies_branch(self):
        result = self.compile_program(
            "flag = True\n"
            "if flag:\n"
            "    print(1)\n"
            "else:\n"
            "    print(2)\n"
        )
        terminator_types = {type(block.terminator) for block in result.ir.main.blocks if block.terminator is not None}
        self.assertIn(JumpTerminator, terminator_types)
        self.assertNotIn(BranchTerminator, terminator_types)


if __name__ == "__main__":
    unittest.main()
