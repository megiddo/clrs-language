# Plan: module imports and packed bytecode executables

Today every `.clrs` file is self-contained except for **link-time** merging: you pass several files to `run` or `compile`, they must declare the same `Module` name (for example `Clrs.Sorting`), and the engine merges procedures and datatypes by **unqualified name**. There is no `import` in source, no workspace root, and no on-disk artifact format beyond raw `.clrsa` text.

---

## Milestone A — Structured imports (Go-style workspace)

**Goal:** Import by **logical module path** (dotted identifiers), not string file paths. A **workspace root** and a small manifest map dot-paths to directories; the compiler walks the graph like `go build`.

### Recommendation (adopt this for M7)

**1. Workspace manifest — `clrs.mod` at the project root**

TOML, one file, no string imports in source:

```toml
module = "clrs.io/book"

[paths]
"Clrs.Sorting" = "lib/sorting"
"Clrs.Heap"    = "lib/heap"
"demo"         = "cmd/demo"
```

- **`module`** — workspace name (like Go’s `module` line in `go.mod`). Used for error messages and, later, versioning of external deps.
- **`[paths]`** — maps a **logical module path** (same spelling as `Module …` in source) to a **directory relative to the manifest**. No `../` in source; all layout is declared here.

Optional later: `require`, `replace`, `exclude` (Go parallels). Not in v1.

**2. On-disk layout (convention + manifest)**

```
clrs.mod
lib/
  sorting/
    insertion-sort.clrs    ▷ first line: Module Clrs.Sorting
    merge.clrs             ▷ Module Clrs.Sorting
  heap/
    heap.clrs              ▷ Module Clrs.Heap
cmd/
  demo/
    main.clrs              ▷ Module demo
```

Every `.clrs` file in a mapped directory must declare the **same** `Module` path as the manifest key for that directory. A file whose `Module` line disagrees with the directory’s key is a **compile error** (like Go’s `package` name vs directory mismatch, but stricter because CLRS uses qualified names).

All files in one directory **merge** into one link unit (same as today’s multi-file CLI merge).

**3. Import syntax — structured only**

```text
Module demo

import Clrs.Sorting
import Clrs.Heap

Run(A)
	InsertionSort(A)
	HeapSort(A)
```

- **`import` + dotted path** — same token sequence as `Module Clrs.Sorting`: identifiers separated by `.`. No quotes, no `from`, no relative paths.
- Imports appear after the `Module` line and before any definition.
- Transitive imports are followed automatically (A imports B, B imports C → compiling A loads C).
- **Circular imports** → compile error with the cycle listed.
- **Visibility (v1):** everything in an imported module is visible. Call sites use **unqualified** names (`MergeSort`, not `Clrs.Sorting.MergeSort`). Local definitions shadow imported names.
- **Duplicate link names** across imported modules → link error (unchanged rule).

**v2 (implemented on `clrs/cleanup`):** `import Clrs.Sorting as Sort` for qualified calls `Sort.MergeSort`, plus `[require]`, `[replace]`, and `[exclude]` in `clrs.mod`.

**4. Resolution algorithm**

1. Find `clrs.mod` by walking upward from the entry file’s directory (like `go.mod`).
2. Parse entry file → read its `Module` path and `import` list.
3. For each imported path, look up `[paths]` in the manifest; if missing, error: `unknown module Clrs.Foo (not in clrs.mod)`.
4. Read every `*.clrs` in that directory, verify `Module` headers, parse, merge.
5. Repeat for imports discovered in those files (depth-first with cycle detection).
6. Compile dependencies before the entry module; link into one routine/datatype table for the run.

**5. CLI**

```bash
clrs run cmd/demo/main.clrs -- '… driver …'
```

- The entry file is the only positional path required; imports come from the manifest.
- Extra `.clrs` paths on the command line remain as an **escape hatch** for experiments, but normal workflows use the manifest only.
- `clrs compile` uses the same graph.

**6. Why Go-ish and not “string imports”**

| Go | CLRS (proposed) |
|---|---|
| `go.mod` `module` + `require` | `clrs.mod` `module` + `[paths]` |
| Import path is a string literal | Import path is **parsed identifiers** (`Clrs.Sorting`) |
| One package per directory | One logical `Module` path per mapped directory |
| `package foo` must match usage | `Module Clrs.Sorting` must match manifest key |
| Compiler resolves import path to `$GOMOD/cache` or module root | Compiler resolves dot-path to manifest directory |

We deliberately **do not** use filesystem strings in source (no `from "../lib"`). Layout changes belong in `clrs.mod`, like moving a Go package and updating imports in `go.mod` / module path, not in every `.clrs` file.

**7. Mapping today’s repo**

A plausible migration for this project:

```toml
module = "clrs.io/local"

[paths]
"Clrs.Sorting" = "lib/sorting"
```

All nine examples already use `Module Clrs.Sorting`; they would live under one mapped directory until split:

```toml
"Clrs.Sorting" = "lib/sorting"
"Clrs.Heap"    = "lib/heap"
```

Move files accordingly; `clrs run cmd/bench/sort.clrs -- …` imports `Clrs.Sorting` without listing eight paths.

**8. Tests for M7**

- Manifest discovery upward from nested entry file.
- Unknown import path fails at compile time.
- `Module` header mismatch with manifest key fails.
- Transitive import (demo → Sorting → internal helper file in same dir).
- Cycle `A imports B`, `B imports A` fails.
- Shadowing: local `InsertionSort` hides imported one.
- Linear search: still blocked until `linear-search.clrs` parses; import design does not fix transcription.

---

## Milestone B — Packed `.clrsa` executable

**Goal:** One file on disk that contains merged bytecode **and** a named entry point, runnable without a driver string on the command line.

### File format (text, extends today’s `.clrsa`)

Add a header and entry directive:

```text
▷ clrsa 1
.module Clrs.Sorting
▷ merged from heap.clrs, max-heapify.clrs, …
.proc HeapSort
…
.end
.entry main
▷ driver lowered to .driver block
.driver
…
.end
```

- **`▷ clrsa 1`** — format version (comment line so old loaders can reject cleanly).
- **`.module Name`** — documents which source module the following blocks came from (optional repeat per section).
- **`.entry <label>`** — names the routine to run: either a `.proc` name or the synthetic `.driver` block.
- Existing `.proc`, `.datatype`, `.driver`, `.local`, opcodes unchanged.

### `compile` today vs pack tomorrow

| Today | Packed |
|---|---|
| `clrs compile a.clrs b.clrs -o out.clrsa` | `clrs pack cmd/demo/main.clrs -- driver -o app.clrsa --entry main` |
| Merged procedures, optional `.driver` appended | Same bytes plus `.entry` and version header |
| `clrs run` needs `-- driver` | `clrs run app.clrsa` runs `.entry` with no driver |

Pack should use the **same import graph** as compile (manifest + entry file), not a manual file list.

### Implementation sketch

1. **Bytecode model:** `Program` gains optional `entry: str | None` and `format_version: int`.
2. **Loader:** after loading blocks, resolve `.entry` to a `Routine`; reject missing or ambiguous entry.
3. **Engine:** `run_entry(program)` instead of always taking driver source text.
4. **CLI:**
   - `clrs compile …` — unchanged semantics (library `.clrsa`, no entry required).
   - `clrs pack <entry.clrs> -- driver -o app.clrsa [--entry name]` — resolve imports, link, write header + `.entry`. Default entry name `main` when a driver is present.
   - `clrs run app.clrsa` — if the argument is a packed `.clrsa` with `.entry`, load and run it; else today’s behavior.
5. **Tests:** round-trip pack → run for insertion sort; entry missing → exit 1; two `.entry` lines → load error.

### Why not binary

Same reasons as the interpreter: diffable, comment-friendly, VS Code grammar already exists. Packing is concatenation + metadata, not a new encoding.

---

## Suggested stack order

1. **M5:** `compile` CLI (done).
2. **M6:** `.param` / arity in `.clrsa` (link table hygiene from M3 notes).
3. **M7:** `clrs.mod` + structured `import Clrs.Sorting` (Milestone A).
4. **M8:** `.clrsa` pack + `run` without driver (Milestone B).

Each milestone keeps the nine-file contract green and adds tests only for the new surface.
