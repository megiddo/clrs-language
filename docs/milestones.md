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

## M3 — Machine

- Branch: `clrs/m03-machine`, from `db7e6a2` (the M2 tip).
- Why: loaded `.clrsa` now runs, so the nine example files can be checked for behavior and not only for text. The `Engine` facade reads real `.clrs` files from disk, parses and compiles each module to `.clrsa` text, loads that text, merges the definitions of every file that declares `Module Clrs.Sorting`, then compiles, loads, and executes a driver string. The tests use the same pipeline, with no fakes. There is no CLI yet (M4).
- Values (`clrs/values.py`): Python `int` and `bool`, checked by exact type so `True` is never `1`; singletons `INFINITY` (Value Object) and `NIL` (Null Object); `UNASSIGNED` (Null Object) for a never-stored slot, so reading one faults while reading a stored `NIL` does not; and `ClrsArray` (Entity), a 1-based array with a fixed length and its own attribute dictionary. `[n]` is `n` nil slots. `length` is structural. Any other attribute faults until written. A datatype's defaults are recorded but never applied.
- Machine (`clrs/machine.py`, `frames.py`, `storage.py`, `arithmetic.py`, `flow.py`): Pattern: Command. Each opcode has its own command object, and the `COMMANDS` table covers every `Opcode`. `Machine.run` loops over an explicit `FrameStack` of `Frame`s (local slots, operand stack, program counter). `CALL` pushes a frame and `RET` pops one, so a CLRS call never recurses in Python. A recursion five times Python's limit runs, and more than 10000 active frames faults. Arguments bind the callee's first slots. `STORE` rebinds only the current frame, and element and attribute writes go to the shared array. `CMP` orders integers and `∞` (`∞` is above every integer and equal to itself), tests booleans by equality and arrays by identity, and faults on `NIL` or mixed kinds. Arithmetic takes integers only. `FLOORDIV` floors (`⌊-3/2⌋` is `-2`) and faults on zero. `JUMP_IF_FALSE` requires a boolean.
- Modules (`clrs/modules.py`): Pattern: Repository. Keeps each module's `.clrsa` text in load order, plus one table of procedures and datatypes. A name defined twice raises `LinkError`.
- Faults: `RuntimeFault` and `LinkError` join `CompileError` and `LoadError` in `clrs/errors.py`. `examples/merge.clrs` is run as written (`R[i]`, `L[i] < R[i]`) and faults on nil. Nothing in the compiler repairs it.
- Known gap: `.clrsa` does not record how many of a routine's locals are parameters. So `CALL` faults only when there are more arguments than slots, and a call with too few arguments, or one that spills into non-parameter locals, is not caught. Fixing this means a format change such as `.param`, left for a later milestone.
- Tests: `tests/test_nine_files.py` (the whole nine-file table through `Engine` on the real files: insertion sort and bubblesort, `merge.clrs` compiles and a real range faults on nil, `MergeSort(A, 1, 1)` leaves `[5,]` unchanged, a wider range with `merge.clrs` faults on nil, `linear-search.clrs` fails on line 5, `left[A, 1]` is 3 and `right[A, 1]` is 4, the heap family gives `[16, 1, 2, 3, 9, 4, 7, 8, 10, 14]` with `contains[A]` 1, and `Heap` records `contains = 0` without applying it); `tests/test_machine.py` (parameter rebind is invisible, element and attribute writes are visible, scalars are values, `i > 0 and A[i] > 0` never reads `A[0]` although `A[0]` alone faults, floor of negative quotients, associativity, `∞` against huge and negative integers, nil comparisons, loop variables surviving at 4 and 0, `for` re-reading its end, alloc versus literal, fresh arrays without `contains`, bounds and type faults, unassigned versus nil, deep calls, the frame limit, arity); `tests/test_runtime.py` (hand-written `.clrsa` for faults the compiler never emits, value objects, and engine merging and lookups). 253 tests in all.
- Coverage: 2234 of 2234 statements in `clrs/` (100%).
- Mutmut 3.8: 3203 killed, 9 timed out, 76 survived, of 3288. Killed is 97.4%. The 12 survivors in the new modules are equivalent. Seven mutate `__init__` arguments of command objects that `machine.py` builds at import time, before mutmut switches mutants. Two change the rank given to `∞` to another value that still sorts above every integer. One changes the machine's initial result, which `RET` always overwrites. Two change the file read encoding, which is the same under a UTF-8 locale. The other 64 are in the M1 and M2 modules, as before.
- Decision logs tested in `tests/test_run_decisions.py`, records only: `run driver`, `call procedure`, `branch through`, `branch taken`, `compare integer`, `compare infinity`, `compare boolean`, `compare identity`, `attribute length`, `attribute stored`, `module open`, `module merge`, `module datatype`, `fault` with `nil`, `order`, `mixed`, `arithmetic`, `zero`, `array`, `index`, `bounds`, `size`, `attribute`, `procedure`, `unassigned`, `condition`, `depth`, `arity`, `fall`, `underflow`, `length`, and `unlinked` with `duplicate`, `module`, `datatype`.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
```

## M4 — CLI

- Branch: `clrs/m04-cli`, from `6424db9` (the M3 tip).
- Why: the M3 `Engine` can now be driven from a shell. `python -m clrs run <files...> -- <driver>` loads each file in order, runs the driver, and prints its last expression and a newline.
- CLI (`clrs/cli.py`, `clrs/__main__.py`): Pattern: Command. `Invocation` parses the argument list: `run`, then zero or more files, then `--`, then exactly one driver argument. Anything else prints the usage line to stderr and exits 2. Each file load and the driver run is a `Stage` labelled with its path or `driver`. The first `CompileError`, `LoadError`, `LinkError`, or `RuntimeFault` prints `<label>: <kind>: <message>` to stderr, prints nothing to stdout, and exits 1. A file that cannot be read prints `<path>: cannot read: <reason>` and also exits 1. `__main__.py` only passes `sys.argv[1:]` to `main` and exits with its status.
- Printer (`clrs/printer.py`): Pattern: Strategy. The printer picks a renderer by exact type, so `True` is never printed as `1`. Integers print in decimal, booleans as `True`/`False`, then `∞`, `NIL`, and arrays as `[v1, v2, …]`. A one-element array prints as `[v,]` and an empty array as `[]`. Elements are printed recursively, so a nested array is shown and a nil slot prints as `NIL` (`[2]` prints `[NIL, NIL]`).
- Tests: `tests/test_cli.py` runs `python -m clrs` in a real subprocess and expects insertion sort to print `[1, 2, 3, 4, 5, 6]` with an empty stderr. The subprocess sets `PYTHONWARNINGS=ignore` because under mutmut the child imports mutmut's trampoline, which warns about deprecated `setup.cfg` keys. The in-process tests cover `runpy` on `__main__` for both a success and a stderr fault, scalars, arrays of length 0, 1, and 2, alloc versus literal, nested arrays, only the last expression printing, the heap family across four files, a compile error in a file (`linear-search.clrs` line 5) and in the driver, a runtime nil fault from `merge.clrs`, a duplicate-definition link error, an unreadable file, the first fault stopping the run, and six malformed command lines. 274 tests in all.
- Coverage: 2321 of 2321 statements in `clrs/` (100%).
- Mutmut 3.8: 3358 killed, 8 timed out, 77 survived, of 3443. Killed is 97.5%. One survivor is in the new modules, and it is equivalent: the initial `result` in `RunCommand._stages`, which the driver stage always overwrites before printing. The other 76 are in the M1 to M3 modules, as before.
- Decision logs tested in `tests/test_cli_decisions.py`, records only: `cli usage`, `cli run`, `cli compile`, `cli link`, `cli runtime`, `cli file`, `print integer`, `print boolean`, `print infinity`, `print nil`, `print array`, and `print single`. `cli load` exists in the fault table, but the command line cannot reach it, because compiled driver text always loads.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
python3 -m clrs run examples/insertion-sort.clrs -- 'A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A'
```
