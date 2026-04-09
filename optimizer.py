"""Legacy compatibility module.

The active optimizer lives in `compiler.optimizer`.
"""

from compiler.optimizer import ConstantFolder


class Optimizer(ConstantFolder):
    pass
