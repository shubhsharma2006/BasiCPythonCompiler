"""Legacy compatibility module.

The active semantic implementation lives in `compiler.semantic`.
"""

from compiler.semantic import SemanticAnalyzer
from compiler.utils.error_handler import ErrorHandler


class SemanticError(RuntimeError):
    pass


class SemanticAnalyser(SemanticAnalyzer):
    def __init__(self):
        self._errors = ErrorHandler("", "<legacy-semantic>")
        super().__init__(self._errors)
        self.defined_vars = set()
        self.symbols = None

    def analyse(self, program):
        model = self.analyze(program)
        if self._errors.has_errors():
            raise SemanticError(self._errors.render())
        self.defined_vars = set(model.globals.keys())
        self.symbols = model
        return model
