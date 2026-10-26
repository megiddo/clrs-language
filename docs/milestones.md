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

## M6 — Parameter slots in `.clrsa`

- Branch: `clrs/m06-param-slots`, from `4e81344` (the phase-2 tip on `clrs/m05-plan-stack`).
- Why: `.clrsa` now records which slots are parameters, so a call with the wrong number of arguments is caught before a run instead of silently binding into ordinary locals.
- Format: each routine lists `.param Name` for every procedure or method parameter, in order, then `.local Name` for every other slot (assigned names, loop variables, and exchange temporaries `$n`), then code. A parameter that is also assigned is a `.param` only. `.driver` blocks have no `.param`. `Routine` gains `parameters` beside `locals` (now non-parameter slots only) and `slots()` for both in order; `Program.text()` writes `.param` lines back out.
- Loader (`clrs/bytecode/blocks.py`, `loader.py`): `.param` is a directive with one operand. It must come before any `.local`, label, or instruction, and a name may be declared only once across `.param` and `.local`. `.param` outside a block, inside a `.datatype`, or inside a `.driver` (`DriverBlock`) is refused. All of these raise `LoadError` with a line number.
- Link (`clrs/run/linker.py`): Pattern: Specification. `Engine.run` checks every `CALL` in every loaded routine and in the driver against the callee's `.param` count before the machine starts. Too few or too many arguments raises `LinkError` (`the driver calls Fact with 2 argument(s), but Fact takes 1.`), even when that call would never run. A callee that is not loaded is left to the machine, which faults only if the call runs, so `MergeSort` without `merge.clrs` still faults with `Merge is not a loaded procedure.` The CLI reports the error as `driver: link error: …` and exits 1. `clrs compile` does not link, because a library's callees may come from files that are not on the command line.
- Machine: a frame binds arguments to `.param` slots only. `CALL` faults at run time unless the argument count equals the parameter count, for hand-written `.clrsa` run on `Machine` directly.
- Known M3 gap closed: a call with too few arguments, or with extra arguments that spill into non-parameter locals, was not caught. Now both are a `LinkError` through the engine and a `RuntimeFault` on unlinked text.
- Editor: `syntaxes/clrsa.tmLanguage.json` highlights `.param` as a directive.
- Tests: snapshots of `insertion-sort.clrs` and `heap.clrs` refreshed (`.param A`, `.param i`); `ParameterTest` in `tests/test_compile.py` (parameters in order, an assigned parameter is not also a local, no `.param` for a zero-parameter procedure or a driver, methods); `.param` round trip and nine new loader faults in `tests/test_load.py`; link-time arity for too many, too few, zero-parameter, an uncalled procedure, and calls across two files in `tests/test_machine.py`; run-time arity on unlinked text, parameter binding, and deferral of an unknown callee in `tests/test_runtime.py`; a CLI link error in `tests/test_cli.py`; `.param` in `tests/test_clrsa_grammar.py`. The nine-file table is unchanged and green. 295 tests in all.
- Coverage: 2498 of 2518 statements in `clrs/` (99%). The 20 missed lines are in the M4/M5 CLI modules; every module changed here is at 100%.
- Mutmut 3.8: 3683 killed, 9 timed out, 50 survived, 10 with no tests, of 3752. Killed is 98.2%. No survivor is in a module changed by M6; the one timeout in a changed module (`Frame.fetch`) makes a frame never advance past its end, which loops until the timeout.
- Decision logs tested in `tests/test_run_decisions.py` and `tests/test_bytecode_decisions.py`, records only: `link call`, `link deferred`, `unlinked arity`, `fault arity` (now on unlinked text), `refuse param` (order and duplicates), `refuse local` (a `.local` that repeats a `.param`), and `refuse block` (`.param` in a driver).

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
python3 -m clrs compile examples/insertion-sort.clrs
```

## M7 — Workspace manifest and structured imports

- Branch: `clrs/m07-imports`, from `33c5fe0` (the M6 tip on `clrs/m06-param-slots`).
- Why: an entry file can now name the modules it needs with `import Clrs.Sorting`, and `clrs run` / `clrs compile` find their files through a `clrs.mod` manifest instead of a hand-written file list.
- Manifest (`clrs/run/manifest.py`, Pattern: Factory Method with a Null Object): `clrs.mod` is TOML with `module = "…"` and a `[paths]` table from dotted module paths to directories relative to the manifest. It is found by walking up from the entry file's directory. Invalid TOML, a missing or non-string `module`, a `paths` that is not a table, a key that is not dotted identifiers, or a non-string directory is a `CompileError` at 1:1 of `clrs.mod`. With no manifest, an entry without imports still runs; any import is a compile error at the import line. The repo root now has `clrs.mod` mapping `"Clrs.Sorting" = "examples"`.
- Syntax (`clrs/front/parser.py`, `ast.py`, `lexer.py`): `import` is a keyword. `import A.B` lines come after `Module` and before the first definition and become `Import(path, line, column)` nodes in `Module.imports`. An import after a definition is rejected; a quoted path is not a token.
- Graph (`clrs/run/imports.py`, Pattern: Builder): depth first from the entry. Each imported path must be a `[paths]` key (`unknown module Clrs.Foo (not in clrs.mod of clrs.io/local).`); its directory must hold `*.clrs` files; every one is parsed and must declare `Module` equal to the key. The entry is checked the same way when its own directory is mapped, but it loads alone, without its siblings. A path already on the walk stack is a cycle (`Import cycle: Clrs.Sorting → Clrs.Heap → Clrs.Sorting.`). A diamond loads the shared module once. The plan lists dependencies first and the entry last.
- Shadowing: a module's top-level definitions hide same-named definitions in any module it imports, directly or transitively. Calls stay unqualified and the link table stays flat, so the hidden definitions are dropped before compiling and `clrs compile` never writes two blocks of one name. Two modules with no import path between them that define one name remain a `LinkError`.
- Faults: `SourceFault` (Pattern: Decorator) names the file behind a compile, load, link, or read failure anywhere in the graph. The CLI prints `<that file>: compile error: …` for it, so a header mismatch in a dependency is reported against the dependency.
- CLI: the first file of `run` and `compile` is the entry and pulls in its imports (`Engine.load_entry`); later files are loaded one by one as before (`Engine.load_extra`), skipping any the graph already loaded as a dependency. Listing the entry twice is still a link error. `Engine.of` and `load_file` ignore imports, so the nine-file tests are unchanged and green.
- Linear search: importing `Clrs.Sorting` from the repo manifest still fails at `examples/linear-search.clrs` line 5; imports do not skip or repair it.
- Editor: `clrs.tmLanguage.json` highlights `import` and the dotted path after it.
- Tests: `tests/test_imports.py` (nested entry, a mapped directory merging several files, transitive imports, diamond, no manifest, entry in a mapped directory, unknown import in the entry and in a dependency, header mismatch of a dependency and of the entry, cycle, self-import, empty directory, parse and compile errors in a dependency, unreadable entry and manifest, every manifest fault, local and transitive shadowing, unrelated duplicates, the repo manifest, linear search through an import, `run` and `compile` through the graph, a listed dependency skipped, extra files, and a `python -m clrs run` subprocess from inside a workspace); `ImportTest` in `tests/test_parse.py`; `ClrsGrammarTest` in `tests/test_clrsa_grammar.py`. 342 tests in all.
- Coverage: 2744 of 2756 statements in `clrs/` (99%). The new and changed modules (`manifest.py`, `imports.py`, `engine.py`, `parser.py`) are at 100%; the 12 missed lines are the pre-existing `main` dispatch and compile usage branches.
- Mutmut 3.8: 4118 killed, 11 timed out, 49 survived, of 4178. Killed is 98.6%. No survivor is in a module added or changed by M7 apart from the untouched `main` dispatcher in `command.py`. The two new timeouts in `ModuleBuilder.parse` replace a parsed import or definition with `None`, which never advances the cursor.
- Decision logs tested in `tests/test_import_decisions.py`, records only: `parse import`, `import manifest`, `import standalone`, `import module`, `import seen`, `module shadow`, `module skip`, and `reject` with `import`, `manifest`, `header`, `cycle`. `tests/test_cli_decisions.py` also asserts `cli file` from `compile`.
- `setup.cfg` copies `clrs.mod` into the mutmut sandbox because a test reads the repo manifest.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg clrs.mod /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
```

## M8 — Packed executable `.clrsa`

- Branch: `clrs/m08-pack-run`, from `b682a2b` (the M7 tip on `clrs/m07-imports`).
- Why: one `.clrsa` file now carries the linked import graph and a named entry point, so `clrs run app.clrsa` runs a program without a driver on the command line.
- Format (`clrs/bytecode/model.py`, `loader.py`, `blocks.py`): line 1 exactly `▷ clrsa <digits>` is the header. Version 1 loads; any other number is a `LoadError` on line 1. Any other `▷ clrsa …` line, or a header on a later line, is an ordinary comment, so unversioned library text loads as before. `.module Name` and `.entry Name` are directives that go between blocks (inside a block they are refused like any misplaced directive). `.module` documents which module the next blocks came from. `.entry` needs the header, may appear once (`A second .entry; the first is on line N.`), and resolves by name (Pattern: Specification, `EntrySpecification`) to exactly one routine: a `.proc` of that name or the one `.driver`. No match, or more than one, is a `LoadError`. `Program` gains `entry: str | None`, `format_version: int` (0 without a header), and `entry_routine()`. `Program.text()` writes the header and `.entry` back before the entry routine.
- Pack (`clrs/run/modules.py`, `engine.py`): `Engine.packed_text(entry)` writes the header, then `.module Name` before each loaded module's listing, then the driver. With a driver, `.entry` comes just before `.driver`, which takes the entry name (default `main`). Without one, `.entry` comes just before `.proc <entry>`. An entry that names both a loaded procedure and the driver, one with neither, or a procedure entry with parameters is a `LinkError` when packing.
- Run (`Engine.load_packed`, `Engine.run_entry`): merges every `.proc` and `.datatype` of the packed program, so a duplicate name is still a `LinkError`. It then checks that the entry takes no parameters, links every `CALL` (M6 arity), and runs the entry on the machine. A program with no `.entry` is a `LinkError` (`There is no .entry to run; write one with clrs pack.`).
- CLI (`clrs/cli/pack_command.py`, `command.py`): `python -m clrs pack <entry.clrs> [files...] [-- <driver>] [-o app.clrsa] [--entry name]`. The first file goes through the M7 import graph like `run` and `compile`. Options come in any order; each may appear once, and the entry must be one word. Output goes to `-o` or stdout. Pack faults print `<file>:`, `driver:`, or `pack: link error: …` and exit 1. `run` with a lone `.clrsa` argument runs it packed, and its faults are labelled with that path. Every other `run` command line behaves as before. `main` now dispatches through a table of the three commands and prints all three usage lines. `clrs compile` is unchanged and writes no header or `.entry`.
- Editor: `clrsa.tmLanguage.json` highlights `.entry` and `.module` as directives and scopes the `▷ clrsa N` header ahead of ordinary comments.
- Tests: `tests/test_pack.py`: the loader's header, version, entry, and module rules plus 13 load faults; a text round trip; insertion sort and the heap family packed and run through `Engine` (the heap result equals a driver run); a procedure entry `Main()` packed through a temporary `clrs.mod` workspace import; the pack and run link errors; CLI pack to a file and to stdout, options in any order, faults, and eight usage lines; packed-run faults for a library blob, a future version, a runtime fault, and a missing file; `run x.clrs` and `run app.clrsa -- 1` keeping their old paths; `main` dispatch; and a `python -m clrs pack` then `python -m clrs run app.clrsa` subprocess printing `[1, 2, 3, 4, 5, 6]`. `tests/test_clrsa_grammar.py` covers `.entry`, `.module`, and the header. The nine-file table is unchanged and green. 373 tests in all.
- Coverage: 2940 of 2944 statements in `clrs/` (99.9%). Every module added or changed by M8 is at 100%. The 4 missed lines are pre-existing branches of `CompileInvocation.parse`.
- Mutmut 3.8: 4592 killed, 9 timed out, 11 survived, of 4612. Killed is 99.6%. Three survivors are in M8 code, and all three are equivalent. One is `argv[:2]` for `argv[:1]` in `main`, which is the same truth test on a non-empty list. The other two change the encoding `load_packed` reads with, which is the same under a UTF-8 locale. The new tests also kill the `main` usage-log and dispatch survivors that M7 left.
- Decision logs tested in `tests/test_pack_decisions.py`, records only: `load packed`, `load module`, `load entry`, `refuse version`, `refuse entry` (no header, missing, second), `pack driver`, `pack procedure`, `unlinked entry`, `cli pack`, `cli packed`, `cli link` from pack, and `cli usage` from `pack` and from `main`.

Commands:

```sh
python3 -m unittest discover -s tests
python3 -m coverage run --source=clrs -m unittest discover -s tests && python3 -m coverage report -m
rm -rf /tmp/clrs-mut && mkdir /tmp/clrs-mut && cp -R clrs clrs_lint tests examples lang editors setup.cfg clrs.mod /tmp/clrs-mut/
(cd /tmp/clrs-mut && python3 -m mutmut run && python3 -m mutmut results)
python3 -m clrs pack lib/sorting/insertion-sort.clrs -- 'A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A' -o build/app.clrsa
python3 -m clrs run build/app.clrsa
```

## Post-merge cleanup — lib/sorting, linear search, import v2

- Branch: `clrs/cleanup`, from merged `master` (`26203e3`, PR #1).
- Why: close the last nine-file transcription gap, adopt the planned `lib/sorting` layout, and ship manifest/import v2 without a new bytecode version.
- Linear search: `lib/sorting/linear-search.clrs` now uses `for i ← 1 to length[A] do`, returns the index or `NIL`. CLI compile-error coverage moved to `tests/fixtures/broken-for.clrs`.
- Layout: all nine contract files live under `lib/sorting/`; repo `clrs.mod` maps `"Clrs.Sorting" = "lib/sorting"` with `[require]`.
- Import v2: `import Clrs.Sorting as Sort`, qualified calls `Sort.Name(…)` (link names `Sort.Name`), plus `[replace]`, `[require]`, and `[exclude]` tables in `clrs.mod`. Shadowing still drops unqualified imports; full modules are recorded for alias registration.
- Editor/docs: VS Code grammar highlights `as`; JetBrains TextMate bundles under `editors/jetbrains/`; README tone restored.
- Tests: 378 tests, all green (`python3 -m unittest discover -s tests`).
