# CLRS interpreter checklist

Source of truth for stacked milestones. Implement **one unchecked milestone**, then stop. Bytecode is plain text (`.clrsa`), not binary.

**Phase 1** (M1–M4): complete on `master`.

**Phase 2** (M5–M8): complete; merged in PR #1.

**Post-merge cleanup** (`clrs/cleanup`): linear-search fix, `lib/sorting` layout, import v2 (`as`, `[require]`, `[replace]`, `[exclude]`).

Read also: [docs/planning/module-import-and-pack.md](planning/module-import-and-pack.md).

This is Python 3.12. Gates: `mutmut` ≥ 80% killed on `clrs/`; line coverage of `clrs/` ≥ 95%. Logger `clrs`, info `decision outcome`, separate log-only tests.

## Locked language (unchanged)

Book glyphs and ASCII aliases; 1-based arrays; pointer semantics; nine-file contract — still green after every milestone.

Do not repair legal transcriptions inside the compiler (except fixing the contract files themselves when the book transcription was wrong).

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

## Phase 2 (done)

M5–M8: compile, `.param`, `clrs.mod` + imports, pack + packed run. See [docs/milestones.md](milestones.md).

---

## Post-merge cleanup (done on `clrs/cleanup`)

- [x] Fix `lib/sorting/linear-search.clrs` to book-style LINEAR-SEARCH (`for i ← 1 to length[A] do`, return index or `NIL`).
- [x] Move the nine-file contract from `examples/` to `lib/sorting/`; repo `clrs.mod` maps `"Clrs.Sorting" = "lib/sorting"`.
- [x] Import v2: `import Clrs.Sorting as Sort`, qualified calls `Sort.Procedure(…)`, manifest `[require]`, `[replace]`, `[exclude]`.
- [x] JetBrains TextMate bundles under `editors/jetbrains/`; whimsical README restored.
- [x] Compile-error CLI tests use `tests/fixtures/broken-for.clrs` instead of the fixed linear-search file.

---

## Orchestrator order (historical)

M6 → M7 → M8 serially. Cleanup stacks on merged `master`.
