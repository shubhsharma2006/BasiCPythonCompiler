import os
import tempfile
import unittest

from compiler import compile_source, execute_source


class PipelineTests(unittest.TestCase):
    def compile_program(self, source: str, run: bool = False):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "program.c")
            result = compile_source(source, filename="inline.py", output=output_path, run=run)
            c_code = result.c_code
            run_output = result.run_output
            rendered = result.errors.render()
            output_exists = os.path.exists(output_path)
            runtime_header_exists = bool(result.runtime_header_path and os.path.exists(result.runtime_header_path))
            runtime_source_exists = bool(result.runtime_source_path and os.path.exists(result.runtime_source_path))
            executable_exists = bool(result.executable_path and os.path.exists(result.executable_path))
            return (
                result,
                c_code,
                run_output,
                rendered,
                output_exists,
                runtime_header_exists,
                runtime_source_exists,
                executable_exists,
            )

    def execute_program(self, source: str):
        result = execute_source(source, filename="inline.py")
        return result, result.run_output, result.errors.render()

    def execute_program_file(self, source: str, extra_files: dict[str, str]):
        with tempfile.TemporaryDirectory() as temp_dir:
            main_path = os.path.join(temp_dir, "main.py")
            with open(main_path, "w", encoding="utf-8") as handle:
                handle.write(source)
            for relative_path, contents in extra_files.items():
                file_path = os.path.join(temp_dir, relative_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as handle:
                    handle.write(contents)
            result = execute_source(source, filename=main_path)
            return result, result.run_output, result.errors.render()

    def test_compile_source_returns_structured_result(self):
        result, c_code, _, rendered, output_exists, runtime_header_exists, runtime_source_exists, _ = self.compile_program("print(1)\n")
        self.assertTrue(result.success, rendered)
        self.assertTrue(output_exists)
        self.assertIsNotNone(result.lexed)
        self.assertIsNotNone(result.parsed)
        self.assertIsNotNone(result.program)
        self.assertGreater(len(result.ir.main.blocks), 0)
        self.assertIsNotNone(result.ir.main.blocks[0].terminator)
        self.assertIsNotNone(result.ssa)
        self.assertTrue(runtime_header_exists)
        self.assertTrue(runtime_source_exists)
        self.assertIn("py_write_int", c_code)
        self.assertIn('#include "py_runtime.h"', c_code)
        self.assertTrue(all(not block.phis for block in result.ir.main.blocks))

    def test_execute_source_returns_bytecode_and_output(self):
        result, run_output, rendered = self.execute_program("print(7)\n")
        self.assertTrue(result.success, rendered)
        self.assertIsNotNone(result.bytecode)
        self.assertIn("PRINT", str(result.bytecode))
        self.assertEqual(run_output.strip().splitlines(), ["7"])

    def test_execute_source_supports_multi_argument_print(self):
        result, run_output, rendered = self.execute_program(
            'print("hello", "world", sep=", ", end="!")\n'
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output, "hello, world!")

    def test_execute_source_supports_f_strings(self):
        result, run_output, rendered = self.execute_program(
            'name = "Ada"\nprint(f"Hello {name}")\n'
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["Hello Ada"])

    def test_execute_source_supports_in_and_is_operators(self):
        result, run_output, rendered = self.execute_program(
            "items = [1, 2, 3]\n"
            "print(2 in items)\n"
            "print(4 not in items)\n"
            "print(items is items)\n"
            "print(items is not [1, 2, 3])\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["True", "True", "True", "True"])

    def test_execute_source_supports_additional_builtins(self):
        result, run_output, rendered = self.execute_program(
            "items = [3, 1, 2]\n"
            "print(sorted(items)[0])\n"
            "print(str(10))\n"
            "print(abs(-4))\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["1", "10", "4"])

    def test_execute_source_supports_local_from_import(self):
        result, run_output, rendered = self.execute_program_file(
            "from util import add\nprint(add(2, 5))\n",
            {"util.py": "def add(a, b):\n    return a + b\n"},
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["7"])

    def test_execute_source_supports_closure_capture(self):
        result, run_output, rendered = self.execute_program(
            "def outer(x):\n"
            "    def inner(y):\n"
            "        return x + y\n"
            "    return inner(5)\n\n"
            "print(outer(7))\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["12"])

    def test_execute_source_supports_basic_try_except(self):
        result, run_output, rendered = self.execute_program(
            "try:\n"
            "    raise \"boom\"\n"
            "except:\n"
            "    print(\"handled\")\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["handled"])

    def test_execute_source_supports_typed_except_with_binding(self):
        result, run_output, rendered = self.execute_program(
            "class MyError:\n"
            "    def __init__(self, message):\n"
            "        self.message = message\n\n"
            "try:\n"
            "    raise MyError(\"boom\")\n"
            "except MyError as err:\n"
            "    print(err.message)\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["boom"])

    def test_execute_source_supports_try_finally_on_return(self):
        result, run_output, rendered = self.execute_program(
            "def compute():\n"
            "    try:\n"
            "        return 7\n"
            "    finally:\n"
            "        print(\"cleanup\")\n\n"
            "print(compute())\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["cleanup", "7"])

    def test_execute_source_runs_finally_before_outer_exception_handler(self):
        result, run_output, rendered = self.execute_program(
            "try:\n"
            "    try:\n"
            "        raise \"boom\"\n"
            "    finally:\n"
            "        print(\"cleanup\")\n"
            "except:\n"
            "    print(\"handled\")\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["cleanup", "handled"])

    def test_execute_source_supports_for_range(self):
        result, run_output, rendered = self.execute_program(
            "for i in range(1, 4):\n"
            "    print(i)\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["1", "2", "3"])

    def test_execute_source_supports_lists_tuples_indexing_and_len(self):
        result, run_output, rendered = self.execute_program(
            "items = [10, 20, 30]\n"
            "pair = (4, 5)\n"
            'word = "hello"\n'
            "print(len(items))\n"
            "print(items[1])\n"
            "print(pair[0])\n"
            "print(word[1])\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["3", "20", "4", "e"])

    def test_execute_source_supports_dicts_sets_and_container_methods(self):
        result, run_output, rendered = self.execute_program(
            'd = {"a": 1, "b": 2}\n'
            "print(d[\"a\"])\n"
            "print(len(d))\n"
            "print(d.get(\"b\"))\n"
            "s = {1, 2}\n"
            "s.add(3)\n"
            "print(3 in s)\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["1", "2", "2", "True"])

    def test_execute_source_supports_classes_attributes_and_methods(self):
        result, run_output, rendered = self.execute_program(
            "class Counter:\n"
            "    def __init__(self, start):\n"
            "        self.value = start\n"
            "    def inc(self):\n"
            "        self.value = self.value + 1\n"
            "        return self.value\n\n"
            "counter = Counter(5)\n"
            "print(counter.value)\n"
            "print(counter.inc())\n"
            "print(counter.value)\n"
        )
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["5", "6", "6"])

    def test_execute_source_reports_unhandled_exception(self):
        result, _, rendered = self.execute_program('raise "boom"\n')
        self.assertFalse(result.success)
        self.assertIn("unhandled exception: boom", rendered)

    def test_compile_source_rejects_imports_for_native_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "program.c")
            result = compile_source("from util import add\nprint(add(1, 2))\n", filename="inline.py", output=output_path)
        self.assertFalse(result.success)
        self.assertIn("native compilation does not support imports yet", result.errors.render())

    def test_compile_source_rejects_nested_functions_for_native_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "program.c")
            result = compile_source(
                "def outer(x):\n"
                "    def inner(y):\n"
                "        return x + y\n"
                "    return inner(1)\n"
                "print(outer(2))\n",
                filename="inline.py",
                output=output_path,
            )
        self.assertFalse(result.success)
        self.assertIn("native compilation does not support nested functions yet", result.errors.render())

    def test_compile_source_rejects_exceptions_for_native_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "program.c")
            result = compile_source(
                "try:\n"
                "    raise \"boom\"\n"
                "except:\n"
                "    print(\"handled\")\n",
                filename="inline.py",
                output=output_path,
            )
        self.assertFalse(result.success)
        self.assertIn("native compilation does not support exceptions yet", result.errors.render())



    def test_forward_reference_compiles(self):
        source = (
            "print(later(5))\n\n"
            "def later(x):\n"
            "    return x + 3\n"
        )
        result, _, run_output, rendered, _, _, _, executable_exists = self.compile_program(source, run=True)
        self.assertTrue(result.success, rendered)
        self.assertTrue(executable_exists)
        self.assertEqual(run_output.strip().splitlines(), ["8"])

    def test_short_circuit_runtime(self):
        source = (
            "def side():\n"
            "    print(99)\n"
            "    return True\n\n"
            "if True or side():\n"
            "    print(1)\n"
        )
        result, _, run_output, rendered, _, _, _, _ = self.compile_program(source, run=True)
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["1"])

    def test_wrong_argument_count_fails(self):
        source = (
            "def add(a, b):\n"
            "    return a + b\n\n"
            "print(add(1))\n"
        )
        result, _, _, rendered, _, _, _, _ = self.compile_program(source, run=False)
        self.assertFalse(result.success)
        self.assertIn("expects 2 arguments, got 1", rendered)

    def test_invalid_syntax_is_fatal(self):
        result, _, _, rendered, _, _, _, _ = self.compile_program("x = 1 $ 2\n", run=False)
        self.assertFalse(result.success)
        self.assertIn("Syntax Error", rendered)

    def test_missing_return_path_is_rejected(self):
        source = (
            "def maybe(x):\n"
            "    if x > 0:\n"
            "        return x\n\n"
            "print(maybe(1))\n"
        )
        result, _, _, rendered, _, _, _, _ = self.compile_program(source, run=False)
        self.assertFalse(result.success)
        self.assertIn("may exit without returning", rendered)

    def test_codegen_uses_lowered_ssa_after_merge_folding(self):
        source = (
            "def choose(flag):\n"
            "    if flag:\n"
            "        x = 1\n"
            "    else:\n"
            "        x = 1\n"
            "    return x + 2\n\n"
            "print(choose(True))\n"
        )
        result, c_code, run_output, rendered, _, _, _, _ = self.compile_program(source, run=True)
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["3"])
        self.assertNotIn(" = x + 2;", c_code)
        self.assertIn("_t7 = 3;", c_code)

    def test_top_level_locals_do_not_emit_unused_globals(self):
        source = (
            "x = 3\n"
            "while x > 0:\n"
            "    print(x)\n"
            "    x -= 1\n"
        )
        result, c_code, run_output, rendered, _, _, _, _ = self.compile_program(source, run=True)
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["3", "2", "1"])
        self.assertNotIn("\nint x = 0;\n", c_code)
        self.assertIn("int x__ssa_", c_code)

    def test_codegen_uses_ssa_value_propagation_for_identities(self):
        source = (
            "def clean(x):\n"
            "    y = x + 0\n"
            "    z = y * 1\n"
            "    return z\n\n"
            "print(clean(7))\n"
        )
        result, c_code, run_output, rendered, _, _, _, _ = self.compile_program(source, run=True)
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["7"])
        self.assertNotIn(" + 0;", c_code)
        self.assertNotIn(" * 1;", c_code)

    def test_codegen_routes_print_through_runtime_helpers(self):
        result, c_code, run_output, rendered, _, _, _, _ = self.compile_program('print(1)\nprint(2.5)\nprint("hi")\n', run=True)
        self.assertTrue(result.success, rendered)
        self.assertEqual(run_output.strip().splitlines(), ["1", "2.5", "hi"])
        self.assertIn("py_write_int(", c_code)
        self.assertIn("py_write_float(", c_code)
        self.assertIn("py_write_str(", c_code)
        self.assertIn('#include "py_runtime.h"', c_code)
        self.assertNotIn('printf("%d\\n", _t', c_code)
        self.assertNotIn('printf("%g\\n", _t', c_code)
        self.assertNotIn('printf("%s\\n", _t', c_code)


if __name__ == "__main__":
    unittest.main()
