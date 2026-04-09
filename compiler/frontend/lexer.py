from __future__ import annotations

import io
import tokenize

from compiler.frontend.source import SourceFile
from compiler.frontend.tokens import LexToken, LexedSource
from compiler.utils.error_handler import ErrorHandler


def lex_source(source: str, filename: str, errors: ErrorHandler) -> LexedSource | None:
    source_file = SourceFile(filename=filename, text=source)
    stream = io.StringIO(source).readline
    tokens: list[LexToken] = []

    try:
        for token_info in tokenize.generate_tokens(stream):
            kind = tokenize.tok_name.get(token_info.type, str(token_info.type))
            tokens.append(
                LexToken(
                    kind=kind,
                    text=token_info.string,
                    line=token_info.start[0],
                    column=token_info.start[1],
                    end_line=token_info.end[0],
                    end_column=token_info.end[1],
                    exact_kind=tokenize.tok_name.get(token_info.exact_type, kind),
                )
            )
    except (tokenize.TokenError, IndentationError) as exc:
        message, location = exc.args if len(exc.args) == 2 else (str(exc), (1, 0))
        errors.error("Lexical", message, location[0], location[1])
        return None

    return LexedSource(source=source_file, tokens=tokens)
