from __future__ import annotations

import os

from compiler.core.types import ValueType, c_type_name


class CRuntimeSupport:
    header_name = "py_runtime.h"
    source_name = "py_runtime.c"

    def include_directive(self) -> str:
        return f'#include "{self.header_name}"'

    def header_source(self) -> str:
        return "\n".join(
            [
                "#ifndef PY_RUNTIME_H",
                "#define PY_RUNTIME_H",
                "",
                "#ifdef __cplusplus",
                'extern "C" {',
                "#endif",
                "",
                "void py_print_int(int value);",
                "void py_print_float(double value);",
                "void py_print_str(const char *value);",
                "",
                "#ifdef __cplusplus",
                "}",
                "#endif",
                "",
                "#endif",
                "",
            ]
        )

    def implementation_source(self) -> str:
        return "\n".join(
            [
                '#include "py_runtime.h"',
                "",
                "#include <stdio.h>",
                "",
                "void py_print_int(int value) {",
                '    printf("%d\\n", value);',
                "}",
                "",
                "void py_print_float(double value) {",
                '    printf("%g\\n", value);',
                "}",
                "",
                "void py_print_str(const char *value) {",
                '    printf("%s\\n", value ? value : "");',
                "}",
                "",
            ]
        )

    def emit_files(self, output_path: str) -> tuple[str, str]:
        directory = os.path.dirname(os.path.abspath(output_path)) or "."
        header_path = os.path.join(directory, self.header_name)
        source_path = os.path.join(directory, self.source_name)

        with open(header_path, "w", encoding="utf-8") as handle:
            handle.write(self.header_source())
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(self.implementation_source())

        return header_path, source_path

    def print_call(self, value_name: str, value_type: ValueType) -> str:
        helper = self._print_helper_name(value_type)
        return f"{helper}({value_name});"

    @staticmethod
    def _print_helper_name(value_type: ValueType) -> str:
        if value_type == ValueType.FLOAT:
            return "py_print_float"
        if value_type == ValueType.STRING:
            return "py_print_str"
        return "py_print_int"

    @staticmethod
    def runtime_type_name(value_type: ValueType) -> str:
        return c_type_name(value_type)
