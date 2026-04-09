"""Legacy compatibility module.

The active C backend lives in `compiler.backend`.
"""

from compiler.backend import CCodeGenerator as CodeGenerator

__all__ = ["CodeGenerator"]
