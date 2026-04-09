# Python Subset Compiler

This repository now has two execution lanes for the current language surface:

- a package-driven VM path for direct execution
- a native path that lowers to C and links against a runtime library

The active pipeline is rooted in `compiler/`.

```text
Python source -> lexer -> parser -> CST -> AST lowering -> semantic analysis -> bytecode VM
                                                      \-> optimization -> IR -> C -> executable
```

## Supported v1 subset

- Integer, float, bool, and string literals
- Variable assignment and augmented assignment
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean expressions: `and`, `or`, `not`
- `if` / `elif` / `else`
- `while`
- VM-only `for` loops over `range(...)`
- Top-level function definitions, calls, returns, recursion, and forward references
- VM-only list and tuple literals
- VM-only indexing for lists, tuples, and strings
- VM-only `len(...)` for lists, tuples, and strings
- VM-only top-level classes with instance fields, attributes, and methods
- VM-only `range(...)`
- VM-only local module imports via `import name` and `from name import symbol`
- VM-only nested functions with closure capture
- VM-only basic `raise` and bare `try/except`
- `print(expr)`
- Single-file native compilation

## Explicitly unsupported in v1

- decorators
- default arguments, keyword arguments, and annotations
- full Python runtime semantics

Current boundary:
- VM execution supports `for` loops over `range(...)` for the current subset
- VM execution supports list/tuple literals, indexing, and `len(...)`
- VM execution supports top-level classes, instance attributes, and methods
- VM execution supports local module resolution for the current subset
- VM execution supports nested functions and lexical closure capture for the current subset
- VM execution supports basic untyped exception handling for the current subset
- native compilation still rejects imports and remains single-file only
- native compilation still rejects lists, tuples, indexing, and `len(...)`
- native compilation still rejects classes, attributes, and methods
- native compilation still rejects nested functions/closures
- native compilation still rejects exceptions
- native compilation still rejects `for` loops

Unsupported features fail compilation with structured diagnostics.

## Usage

```bash
# Install in editable mode
pip install -e .

# Run through the VM (default)
python3 main.py test_input.py

# Check only
python3 main.py test_input.py --check

# Compile to native C artifacts
python3 main.py test_input.py --compile-native

# Compile and run natively
python3 main.py test_booleans.py --run --no-viz

# Quiet mode for automation
python3 main.py test_input.py --compile-native --no-viz -q

# Debug dumps
python3 main.py test_input.py --dump tokens
python3 main.py test_input.py --dump bytecode
python3 main.py test_input.py --compile-native --dump ir

# Module / installed entrypoint
python3 -m compiler test_input.py
python-subset-compiler test_input.py
```

The `--no-viz` flag is kept for CLI compatibility but AST visualization is no longer part of the active architecture.

## Project shape

- `main.py`: compatibility entrypoint
- `compiler/frontend`: source handling, lexer, parser, CST, and AST lowering
- `compiler/semantic`: symbol collection, binding resolution, type checking, and control-flow checks
- `compiler/vm`: bytecode lowering and VM execution
- `compiler/optimizer`: safe AST-level folding
- `compiler/ir`: CFG-based lowering with explicit basic blocks and branch terminators
- `compiler/backend`: native C code generation
- `compiler/runtime`: emitted native runtime support files
- `compiler/cli`: command-line entrypoint
- `run_tests.py`: integration and negative test suite

## Test suite

Run unit and integration coverage with:

```bash
python3 -m unittest discover -s tests -v
python3 run_tests.py
```

The suite covers:

- successful compilation and execution for valid subset programs
- VM execution for the current language surface
- VM execution for `for` loops over `range(...)`
- VM execution for list/tuple literals, indexing, and `len(...)`
- VM execution for top-level classes, attributes, and methods
- VM execution for local imports, closures, and basic exceptions
- short-circuit correctness
- forward references and recursion
- compile-time rejection of unsupported syntax and mixed invalid operations
- CLI VM and native modes

GitHub Actions CI is defined in `.github/workflows/ci.yml` and runs both suites on Python 3.10 and 3.11.
