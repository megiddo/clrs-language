# CLRS interpreter checklist

Source of truth for the stacked milestones. Implement one unchecked milestone, then stop. The bytecode is plain text (`.clrsa`), not a binary encoding.

Stack base: `master`. Each branch stacks on the previous milestone tip.

This is Python 3.12, not a Slim app. The mutation gate is `mutmut` at 80% killed on `clrs/`. The coverage gate is 95% line coverage of `clrs/`. Do not install PHP, Infection, or a database. Decision logging uses the standard library `logging` logger named `clrs`.

## Locked language

- Book glyphs and ASCII aliases are the same tokens. Longest alias wins: `<->` before `<-`, `|>` before `|.`, `.Inf`, `<=`, `>=`, `!=`, `|.`, `.|`, `|^`, `^|`. `^` is a caret, never a backtick.
- `▷` and `|>` comment to end of line and emit no token. A comment-only line does not change the indent stack.
- First indented code or comment line fixes the unit: one tab, or two spaces. A mix, a one-space indent, or a jump of more than one level is a compile error.
- Arrays are 1-based. `[n_1 + 1]` and `[5]` allocate that many nil slots. `[5, 2, 4, 6, 1, 3]` is a literal. `[5,]` is a one-element literal. `[]` is an empty literal.
- `length[A]` is the structural length. `contains[A]` is an attribute once a datatype default declares `contains`. A local shadows an attribute. `length` cannot be shadowed or stored.
- `left[A, i]` is a call because of the comma. `A[i]` is an index because `A` is a local. `Name[single]` is never a call.
- `and` binds looser than comparison and short-circuits. `i > 0 and A[i] > key` is `(i > 0) and (A[i] > key)`.
- `+` and `-` are left-associative and looser than `*`. `q - p + 1` is `(q - p) + 1`. `i + 1 * 2` is `i + (1 * 2)`. Comparisons do not chain.
- `/` is legal only as the operator directly inside `⌊ ⌋`. `⌊(p + r)/2⌋` is floor-division. Ceiling, `or`, and a bare floor of a non-division are rejected.
- `for` initializes once, retests the end expression every iteration, steps after the body, and the variable survives. Missing `to`/`downto`, or a missing end expression, is a compile error.
- Only a header opens a suite: `for`, `while`, `if`, `else`, `datatype`, a procedure, a method. An assignment does not.
- Arrays pass as pointers. Rebinding a parameter is local. Element and attribute writes are shared. Scalars are immutable values.
- `nil` is not an integer. Comparing nil is a runtime fault. `∞` is greater than every integer and equal to itself.
- A module file does not run. A driver is `statement; statement; expression`.

## The nine files

`examples/mergesort.clrs` is indented legally: the three calls are siblings of `q ← …` inside the `if`. `examples/linear-search.clrs` is `for i ← length[A] to` with no end expression and does not compile.

| File | Behavior |
|---|---|
| `insertion-sort.clrs` | `[5, 2, 4, 6, 1, 3]` becomes `[1, 2, 3, 4, 5, 6]` |
| `bubblesort.clrs` | same input, same result |
| `merge.clrs` | compiles; a real range raises on comparison with nil |
| `mergesort.clrs` | `MergeSort(A, 1, 1)` leaves a one-element array unchanged; a wider range, with `merge.clrs` loaded, raises on nil |
| `linear-search.clrs` | compile error on line 5 |
| `heap.clrs` | `left[A, 1]` is 3 and `right[A, 1]` is 4 |
| heap family | input `[4, 1, 3, 2, 16, 9, 10, 14, 8, 7]` finishes as `[16, 1, 2, 3, 9, 4, 7, 8, 10, 14]` and `contains[A]` is 1 |

Do not repair a legal transcription inside the compiler. Do not revert the example edits.

## Textual bytecode (`.clrsa`)

The compiler's output is text. The loader reads that text. Comments start with `▷`. Labels are names. The loader resolves them.

```
.proc InsertionSort
.local A
.local j
▷ for j ← 2 to length[A]
CONST 2
STORE j
L_for:
LOAD j
LOAD A
LOAD_ATTR length
CMP le
JUMP_IF_FALSE L_for_end
RET
.end
```

Directives: `.proc Name`, `.local Name` in slot order, `.end`. Opcodes: `CONST`, `LOAD`, `STORE`, `LOAD_IDX`, `STORE_IDX`, `LOAD_ATTR`, `STORE_ATTR`, `ADD`, `SUB`, `MUL`, `FLOORDIV`, `CMP`, `JUMP`, `JUMP_IF_FALSE`, `CALL`, `RET`, `ALLOC`, `PACK`, `POP`. `CONST` operands include integers, `True`, `False`, `NIL`, `∞`. `CALL Name arity`. `CMP` takes `lt`, `gt`, `le`, `ge`, `eq`, or `ne`.

## Design bar

- Every module and every class docstring starts with `Pattern:` and names a pattern the type actually uses: Facade, Builder, Visitor, Strategy, Value Object, Command, Null Object, Factory, Iterator, Repository, Observer, Template Method, Entity, or Enumeration.
- No `Optional` in a signature. No test fake standing in for the lexer, parser, compiler, or machine. The nine-file tests run the real pipeline.
- Methods stay under 80 lines. Classes stay under 500.
- Tests assert meaning: associativity, short-circuit, alloc versus literal, pointer versus rebind, loop-variable survival, floor of a negative quotient, nil, infinity. A test that only asserts a constructor stored its argument is not enough.
- Decision branches log `decision outcome` at info on logger `clrs`. A separate test asserts those records and does not also assert the user-visible result.

## Gates, every milestone

1. `python3 -m unittest discover -s tests` with no filter. Existing linter tests stay green.
2. Line coverage of `clrs/` at or above 95%. `coverage` 7.15 is installed.
3. `mutmut` killed at or above 80% on `clrs/`. Install `mutmut` if it is missing. Do not lower the gate. Record killed, surviving, and the percentage.
4. Append a section to `docs/milestones.md`: branch, why, coverage fraction, mutmut score, and which decision logs were tested.
5. Exactly one commit. Do not push. Do not change git config. Do not commit `.idea/` or `build/`. Do not stage `lang/preprocessor_001.sh` or `lang/tokenizer.php`; their diffs are empty. Do stage the example edits.

## Milestones

### M1 — Lex and parse

- [x] Branch `clrs/m01-lex-parse` from `master`.
- Lexer, indent strategy, alias table, parser, AST, compile errors, decision log.
- AST nodes are frozen value objects with `accept` so a later visitor does not rewrite them. Parse both module files and drivers.
- Commit the example edits, `clrs_lint/`, `editors/vscode/`, and `tests/test_lint.py` so the transcription tools are not left untracked. Mutation and coverage gates apply to `clrs/` only.
- Do not compile, assemble, or execute.

### M2 — Textual bytecode

- [ ] Branch `clrs/m02-text-bytecode` from the M1 tip.
- A visitor lowers the AST to `.clrsa`. A loader reads `.clrsa` back into instructions and resolves labels. Round-trip the text.
- Add a TextMate grammar for `.clrsa` on the existing extension: opcodes, labels, directives, `▷` comments.
- Prove, in the text itself: `and` is two conditional jumps and the right operand is not before the first jump; a `for` re-reads its end expression on each test; `[n_1 + 1]` is `ALLOC`; `[5, 2, 4, 6, 1, 3]` is `CONST`s then `PACK 6`; an exchange evaluates each address expression once.
- Do not run the nine algorithms yet.

### M3 — Machine

- [ ] Branch `clrs/m03-machine` from the M2 tip.
- Values, array entity, command-per-opcode, explicit frame stack. Facade `Engine` loads real files and runs a driver through lex, parse, textual bytecode, load, and execute.
- The nine-file table above is green, through that facade, with no fakes.
- Also lock: parameter rebind is invisible to the caller; element write is visible; `i > 0 and A[i] > key` does not read index 0; `⌊-3/2⌋` is `-2`; `∞` compares above every int; a loop variable survives; `contains` is absent on a fresh array until written; `Heap` records default `contains = 0` and does not apply it.

### M4 — CLI

- [ ] Branch `clrs/m04-cli` from the M3 tip.
- `python -m clrs run <files> -- <driver>` prints the last expression. Integers in decimal. `True`, `False`, `NIL`, `∞`. Arrays as `[v1, v2, …]`, length 1 as `[v,]`, length 0 as `[]`.
- One test runs insertion sort through the command line and expects `[1, 2, 3, 4, 5, 6]`. Compile and runtime faults print to stderr and exit 1.
