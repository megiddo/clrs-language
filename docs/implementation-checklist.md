# CLRS interpreter checklist

Source of truth for stacked milestones. Implement **one unchecked milestone**, then stop. Bytecode is plain text (`.clrsa`), not binary.

**Phase 1** (M1–M4): complete on branches `clrs/m01-lex-parse` … `clrs/m04-cli`.

**Phase 2** (M5–M8): stack each branch on the previous milestone tip. Current stack tip: `clrs/m05-plan-stack` after M5 and this checklist land.

Read also: [docs/planning/module-import-and-pack.md](planning/module-import-and-pack.md).

This is Python 3.12. Gates: `mutmut` ≥ 80% killed on `clrs/`; line coverage of `clrs/` ≥ 95%. Logger `clrs`, info `decision outcome`, separate log-only tests.

## Locked language (unchanged)

Book glyphs and ASCII aliases; 1-based arrays; pointer semantics; nine-file contract in phase 1 table — still green after every milestone.

Do not repair legal transcriptions inside the compiler. `examples/linear-search.clrs` remains a compile error until the example is fixed.

## Design bar (unchanged)

`Pattern:` on every class/module. No `Optional` in signatures. No lexer/parser/VM fakes in nine-file tests. Methods &lt; 80 lines, classes &lt; 500.

## Gates, every milestone

1. `python3 -m unittest discover -s tests` (no filter).
2. Line coverage of `clrs/` ≥ 95%.
3. `mutmut` on `clrs/` ≥ 80% killed (run on `/tmp` copy if Google Drive — see `docs/milestones.md`).
4. Append `docs/milestones.md`.
5. One commit. Do not push. Do not commit `.idea/`, `build/`, or empty-diff `lang/*.php` / `lang/*.sh`.

---

## Phase 1 (done)

| Milestone | Branch | Done |
|---|---|---|
| M1 Lex + parse | `clrs/m01-lex-parse` | [x] |
| M2 Text `.clrsa` | `clrs/m02-text-bytecode` | [x] |
| M3 Machine | `clrs/m03-machine` | [x] |
| M4 CLI `run` | `clrs/m04-cli` | [x] |

---

## Phase 2

### M5 — Compile-only CLI

- [x] Branch stacked on `clrs/m04-cli` layout commit (`cb6bd89`) or same line.
- `python3 -m clrs compile <files...> [-o file.clrsa] [-- <driver>]`
- Writes merged module `.clrsa` to `-o` or stdout; optional driver block appended like `run`.
- `CompileCommand`, `Engine.compiled_text()` / `ModuleRepository.bundle()`.
- Tests in `tests/test_cli.py` and decision log for `cli compile`.

### M6 — Parameter slots in `.clrsa`

- [x] Branch `clrs/m06-param-slots` from phase-2 tip.
- Chosen layout: all `.param` lines first, then `.local` lines, then code. A `.param` after a `.local`, a label, or an instruction is a `LoadError`; so is `.param` in a `.driver` block.
- Chosen layer: link time. `Engine.run` checks every `CALL` against its callee's `.param` count before the machine starts (`clrs/run/linker.py`), so a mismatch is a `LinkError` even if the call never runs. A callee that is not loaded is left to the machine. The machine still checks exact arity at run time for hand-written `.clrsa` that never goes through the engine.
- Add `.param Name` directives after `.local` block (or interleaved: all `.param` then `.local` temps — pick one, document in checklist when done). Parameters are the first N slots; `.local` lists only non-parameter locals including temps.
- Compiler emits `.param` for each procedure/method parameter in order.
- Loader: `CALL` arity must match parameter count; too few or too many arguments is **LinkError** at load or link time (choose one layer, test both paths if split).
- Update `.clrsa` TextMate grammar and `tests/test_clrsa_grammar.py`.
- Refresh bytecode snapshot tests; nine-file table still green.
- Document the known M3 gap closure in `docs/milestones.md`.

### M7 — Workspace manifest + structured imports

- [ ] Branch `clrs/m07-imports` from M6 tip.
- **`clrs.mod`** at workspace root (TOML): `module = "…"` and `[paths]` mapping dotted module paths to directories relative to manifest.
- **Import syntax:** after `Module` line, before definitions: `import Clrs.Sorting` (dotted identifiers only — no string paths).
- Find manifest by walking upward from entry file (like `go.mod`).
- Every `*.clrs` in a mapped directory must declare the same `Module` path as the manifest key; else compile error.
- Transitive imports, cycle detection, topological compile. Unqualified calls; locals shadow imports; duplicate defs → link error.
- **`clrs run entry.clrs -- driver`** resolves imports without listing dependency files on CLI (extra CLI files remain optional override for dev).
- **`clrs compile entry.clrs -o out.clrsa`** uses the same graph.
- Add repo `clrs.mod` mapping `"Clrs.Sorting" = "examples"` (or split `lib/sorting` later); tests: nested entry path, unknown import, header mismatch, cycle, shadowing.
- Parser: `Import` AST node; extend vscode grammar for `import`.
- Linear search example still compile-errors until fixed; do not “fix” via import magic.

### M8 — Packed executable `.clrsa`

- [ ] Branch `clrs/m08-pack-run` from M7 tip.
- Packed format (text): leading `▷ clrsa 1`, optional repeated `.module Name` sections, existing blocks, plus **`.entry <name>`** before the entry routine (`.proc` name or `.driver`).
- **`clrs pack <entry.clrs> -- <driver> -o app.clrsa [--entry main]`** — resolve imports (M7), link, write header + `.entry`. Default entry name `main` when a driver is supplied.
- **`clrs run app.clrsa`** — if single argument is a packed file with `.entry`, load and execute entry (no `-- driver`). `.clrsa` without `.entry` behaves as today (library blob) or errors clearly.
- Loader/Program: `entry: str | None`, `format_version: int`.
- `Engine.run_entry(program)` or equivalent.
- Tests: pack → run insertion sort; missing entry; duplicate `.entry`; subprocess `clrs run app.clrsa`.
- **`clrs compile`** unchanged (library output, no required entry).

---

## Orchestrator order

M6 → M7 → M8 serially. Each worker reads this file and [module-import-and-pack.md](planning/module-import-and-pack.md).
