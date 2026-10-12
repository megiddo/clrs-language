# Milestones

## M1 — Lex and parse

- Branch: `clrs/m01-lex-parse`, from `ee72845`.
- Why: the lexer, indent strategy, alias table, parser, frozen AST, compile errors, and decision log that every later milestone compiles from. Module files and drivers both parse. Nothing compiles, assembles, or runs yet. This commit also tracks the transcription tools (`clrs_lint/`, `editors/vscode/`, `tests/test_lint.py`) and the two example edits.
- Fixes during review: a datatype member named `length` is now rejected, and `TokenCursor.see` lost an unreachable guard.
- Tests: `tests/test_lex.py`, `tests/test_parse.py`, `tests/test_decisions.py`, plus the existing `tests/test_lint.py`. 121 tests. They parse the real `examples/*.clrs` files and cover: longest alias, `+`/`-` left associativity, `*` over `+`, `and` looser than comparison, `[5]` allocate versus `[5, 2]` literal versus `[5,]` versus `[]`, call versus index versus attribute, comment-only lines leaving the indent stack alone, tab and two-space files lexing to the same structure, mixed/one-space/jumped indents, indent under an assignment, `linear-search.clrs` failing on line 5, the legal `mergesort.clrs`, the `Heap` datatype, and a semicolon driver.
- Coverage: 1076 of 1076 statements in `clrs/` (100%).
- Mutmut 3.8: 1380 killed, 8 timed out, 61 survived, of 1449. Killed is 95.2%. The survivors are mostly equivalent: fields of an indent measure that is rejected before use, the alias sort key (reverse lexical order also puts each prefix after its extension), and comment cuts at offset 0, which a comment-only line never reaches.
- Decision logs tested in `tests/test_decisions.py`, records only: `parse module`, `parse driver`, `indent tab` and `indent spaces` once per file, `comment keep`, `array allocate`, `array literal`, `bracket call`, `bracket index`, `bracket attribute`, `floor division`, `for up`, `for down`, and `reject` with `or`, `chain`, `ceiling`, `floor`, `slash`, `length`, `target`, `for`, `indent`.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
# mutmut writes a mutants/ tree; run it on a copy outside Google Drive
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang setup.cfg /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
```

## M2 — Textual bytecode

- Branch: `clrs/m02-text-bytecode`, from `a5dea9d` (the M1 tip).
- Why: the frozen AST now lowers to plain-text `.clrsa` and reads back into instruction objects, so the M3 machine can run text it can show. Nothing executes yet.
- Compiler (`clrs/compiler.py`, `control.py`, `lowering.py`, `addresses.py`, `listing.py`, `locals.py`): visitors over the M1 `accept` methods. Each statement is preceded by a `▷` comment holding its source line, written once per line. Locals are declared in slot order: parameters, then names in first-assignment or loop-variable order, then the exchange temporaries `$1`… (`$` cannot appear in a CLRS name). A procedure ends `CONST NIL`, `RET`. A driver ends with its final expression and `RET`. Labels are `L_<kind>_<n>`, numbered per routine. A name that is never a local is a compile error.
- Directives beyond the checklist's three: `.driver` (no name) for a driver, and `.datatype Name Base` with `.default name constant` lines, closed by `.end`. Datatype methods follow as ordinary `.proc` blocks. A default must be a literal.
- Lowering choices: `and` as a condition is one `JUMP_IF_FALSE` per operand to the same false label; as a value it adds `CONST True`/`CONST False` arms. Unary minus is `CONST 0`, operand, `SUB`. `for` stores the start once, then the label, then reloads the variable and re-evaluates the end expression before `CMP le` (up) or `CMP ge` (down); the step (`ADD`/`SUB`, from the direction strategy) follows the body. An exchange spills each address expression (array and index, or owner) to a temporary once, saves the left value, then writes both sides from the temporaries.
- Loader (`clrs/loader.py`, `blocks.py`, `operands.py`): strips `▷` to end of line, reads blocks into `Routine` and `DatatypeRecord` value objects inside a `Program`, types `CONST` operands (`IntegerConstant`, `BooleanConstant`, `NilConstant`, `InfinityConstant`, so `1` and `True` differ), checks `LOAD`/`STORE` against declared locals, and resolves each jump to a `Target(label, index)`. Faults raise `LoadError` with a line number: unknown opcode or directive, operand count, bad constant/count/comparison, undeclared local, undefined or duplicate label, duplicate local, `.local` after code, misplaced blocks, and a missing `.end`. `Program.text()` writes the loaded program back without comments.
- Editor: `editors/vscode` registers `.clrsa` with `syntaxes/clrsa.tmLanguage.json` (opcodes, jumps, labels, directives, constants, comparisons, `▷` comments) and a language configuration with `▷` line comments and `.proc`…`.end` folding.
- Tests: `tests/test_compile.py` (snapshots of `insertion-sort.clrs` and `heap.clrs`; text proofs that `and` is two conditional jumps with the right operand after the first; a `for` re-reads `length[A]` after its label and only there; `[n_1 + 1]` is `ALLOC`; `[5, 2, 4, 6, 1, 3]` is six `CONST`s then `PACK 6`; `[5]`/`[5,]`/`[]`; `A[F(x)] ↔ A[G(y)]` calls each of `F` and `G` once; plus associativity, `⌊-3/2⌋`, constants, comparisons, if/else, call statements, the legal `mergesort.clrs` siblings), `tests/test_load.py` (hand-built expected routines with resolved targets, the `for` back jump landing on the end re-read, typed constants, every opcode, comments and blank lines ignored, and a text round trip of all eight compilable examples and five drivers), and `tests/test_clrsa_grammar.py`. 174 tests in all.
- Coverage: 1799 of 1799 statements in `clrs/` (100%).
- Mutmut 3.8: 2541 killed, 8 timed out, 66 survived, of 2615. Killed is 97.2%. The 10 survivors in the new modules are equivalent: initial counters and address fields that are always overwritten before use (`reset_temporaries` runs before every exchange, `bind` before every load), and the empty local list handed to the datatype constant reader. The other 56 are in the M1 modules, as before.
- Decision logs tested in `tests/test_bytecode_decisions.py`, records only: `compile module`, `compile driver`, `routine procedure`, `routine method`, `datatype default`, `condition and`, `condition value`, `and value`, `if bare`, `if else`, `address name`, `address index`, `address attribute`, `reject name`, `reject default`, `load procedure`, `load driver`, `load datatype`, `load comment`, `load label`, `label resolve`, and `refuse` with `block`, `directive`, `opcode`, `operands`, `constant`, `local`, `count`, `comparison`, `label`.
- `setup.cfg` now copies `editors/` into the mutmut sandbox because the grammar test reads it. As in M1, mutmut runs on a `/tmp` copy because its `mutants/` tree is slow and unreliable inside Google Drive.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
```
