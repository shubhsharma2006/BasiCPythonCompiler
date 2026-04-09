from __future__ import annotations

from dataclasses import dataclass
import sys


@dataclass
class CompilerIssue:
    kind: str
    message: str
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None

    @property
    def label(self) -> str:
        return f"{self.kind} Error"


class ErrorHandler:
    def __init__(self, source: str = "", filename: str = "<stdin>"):
        self.source_lines = source.splitlines()
        self.filename = filename
        self.errors: list[CompilerIssue] = []
        self.warnings: list[CompilerIssue] = []

    def error(
        self,
        kind: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
        end_line: int | None = None,
        end_column: int | None = None,
    ) -> None:
        self.errors.append(CompilerIssue(kind, message, line, column, end_line, end_column))

    def warning(
        self,
        kind: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
        end_line: int | None = None,
        end_column: int | None = None,
    ) -> None:
        self.warnings.append(CompilerIssue(kind, message, line, column, end_line, end_column))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def format_issue(self, issue: CompilerIssue) -> str:
        location = self.filename
        if issue.line is not None:
            location += f":{issue.line}:{(issue.column or 0) + 1}"
        return f"{location}: {issue.label}: {issue.message}"

    def render(self) -> str:
        lines: list[str] = []
        for issue in [*self.warnings, *self.errors]:
            lines.append(self.format_issue(issue))
            if issue.line is not None and 1 <= issue.line <= len(self.source_lines):
                source_line = self.source_lines[issue.line - 1]
                lines.append(f"  {issue.line:4} | {source_line}")
                if issue.column is not None:
                    width = max(1, (issue.end_column or issue.column + 1) - issue.column)
                    pointer = " " * issue.column + "^" * width
                    lines.append(f"       | {pointer}")
        return "\n".join(lines)

    def report(self, file=sys.stderr) -> None:
        text = self.render()
        if text:
            print(text, file=file)
