"""Run the transcription linter over files or stdin."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from clrs_lint.lint import lint_path, lint_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clrs_lint")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    if args.paths:
        diagnostics = [item for raw in args.paths for item in lint_path(Path(raw))]
    else:
        diagnostics = lint_text(sys.stdin.read(), "<stdin>")
    _emit(diagnostics, as_json=args.json)
    return 1 if diagnostics else 0


def _emit(diagnostics: list, as_json: bool) -> None:
    if as_json:
        json.dump([item.to_json() for item in diagnostics], sys.stdout)
        sys.stdout.write("\n")
        return
    for item in diagnostics:
        print(f"{item.file}:{item.line}:{item.column}: {item.message}")


if __name__ == "__main__":
    sys.exit(main())
