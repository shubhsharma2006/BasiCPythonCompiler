"""Legacy compatibility module.

The compiler now parses Python source via the stdlib `ast` module rather than a
custom token stream. This module remains only to make the migration explicit.
"""


def tokenize(_source: str):
    raise RuntimeError("tokenize() is deprecated; use compiler.frontend.parse_source() instead")
