"""Legacy compatibility module.

The active parser stage lives in `compiler.frontend.parse_tokens`, and AST
lowering lives in `compiler.frontend.lower_cst`.
"""

from compiler.frontend import lex_source, lower_cst, parse_tokens
from compiler.utils.error_handler import ErrorHandler


def parse(source: str):
    errors = ErrorHandler(source, "<legacy-parser>")
    lexed = lex_source(source, "<legacy-parser>", errors)
    parsed = parse_tokens(lexed, errors) if lexed is not None else None
    program = lower_cst(parsed, errors) if parsed is not None else None
    if errors.has_errors():
        raise SyntaxError(errors.render())
    return program
