# Project layout

The interpreter is a pipeline. Packages follow that pipeline; the flat `clrs/` root is only the public facade and `python -m clrs` entry.

```
clrs/
  __init__.py          Public API: parse, compile, load, Engine
  __main__.py

  common/              Cross-cutting
    errors.py          Compile, load, link, runtime faults
    decisions.py       Logger `clrs` decision records

  front/               Source text → AST
    aliases.py         ASCII → book glyphs (longest match)
    tokens.py          Token kinds and lexemes
    indent.py          Tab vs two-space strategy
    lexer.py
    cursor.py
    ast.py             Frozen value objects + accept()
    direction.py       for to / downto strategies
    scope.py
    expressions.py
    statements.py
    parser.py

  bytecode/            AST → textual .clrsa → Program
    model.py           Opcodes, instructions, routines
    locals.py          Slot assignment
    lowering.py        Expression lowering
    addresses.py       lvalues
    control.py         Statements and loops
    listing.py         .clrsa line builder
    compiler.py
    blocks.py          Loader block parser
    operands.py
    loader.py

  vm/                  Program → values
    values.py
    storage.py         LOAD, STORE, ALLOC, …
    arithmetic.py
    flow.py            CALL, JUMP, RET
    frames.py
    machine.py         Command dispatch

  run/                 Files on disk
    manifest.py        Find and read clrs.mod
    imports.py         Import graph → dependency-first load plan
    modules.py         Merge Clrs.Sorting modules
    linker.py          CALL arity against .param
    engine.py          Lex → parse → compile → load → run

  cli/
    command.py         `clrs run`
    compile_command.py `clrs compile`
    printer.py         Driver result formatting

clrs.mod               Workspace manifest: dotted module path → directory

clrs_lint/             Transcription linter (structure only)
editors/vscode/        .clrs and .clrsa highlighting + alias rewrite
examples/lib/sorting/  The nine-file language contract (Module Clrs.Sorting)
tests/                 Real pipeline; no lexer/parser fakes
```

Import rule: outside tests, prefer `from clrs import …` or the subpackage facades (`clrs.front`, `clrs.bytecode`, `clrs.vm`, `clrs.run`, `clrs.cli`, `clrs.common`). Tests may import internals when asserting one layer.
