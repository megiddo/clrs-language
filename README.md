# clrs-language

This is a verbatim implementation of the CLRS pseudocode language.

It was written by an LLM, but I made it pinkie swear that it would use its "Senior Engineer" persona, so the code should be pretty lit.

No creature of God was involved in the composition, though, so I really can't verify.

## Why?

When I was in Analysis of Algorithms last millennium, my professor boldly claimed that this (paraphrasing) was "pseudocode that is not designed to be a real language".

Well, challenge accepted. I spent the next 25+ years thinking about this yak shave, occasionally learning how to write interpreters, compilers, and so on.

Now, by the grace of our savior Claude, I don't have to actually finish learning and apply that stuff. I just get my dumb toy and you can have some, too!

## Design features I politely asked for

*Caveat emptor: there's no way to know if this is what we got. I could read the code, but … I mean. C'mon.*

- Syntax highlighting in VS Code. Probably the most important part.
- Automatic conversion of digraphs and trigraphs into the symbols that match the book. Probably the most important part.
- Conversion to plaintext bytecode for a stack machine to see what happens during compilation. I originally wanted the clanker to write this in Forth, but it complained a lot about that choice. Given how lazy *I* am, it felt unfair to grind its nose into Forth just for the lulz. The syntax highlighting should work here, too. Probably the most important part.
- All nine typed-in examples compile and run (modulo heap child-index transcription, which we execute as written). If those nine are representative of the book syntax, we're gtg.

## Usage

### Install syntax highlighting

**VS Code:** Command Palette → **Developer: Install Extension from Location** → choose `editors/vscode`.

**JetBrains (IntelliJ, PyCharm, …):** enable the **TextMate Bundles** plugin, then **Settings → Editor → TextMate Bundles → +** and select the folder **`editors/jetbrains/intellij-textmate`** (not the `.tmbundle` packages—those often fail in the file picker). If import still fails, see [editors/jetbrains/README.md](editors/jetbrains/README.md).

### Example usage

Run a driver over the sorting library:

```bash
python3 -m clrs run lib/sorting/insertion-sort.clrs -- 'A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A'
```

Compile to textual bytecode (stdout, or `-o`):

```bash
python3 -m clrs compile lib/sorting/insertion-sort.clrs -o build/insertion-sort.clrsa
python3 -m clrs compile lib/sorting/heap.clrs lib/sorting/heapsort.clrs -o build/heapsort.clrsa
```

### Module imports

Imports are **structured dotted paths**, not string file paths (Go-style workspace, not `from "../lib"`).

1. Put a **`clrs.mod`** at the project root (the compiler walks upward from the entry file until it finds one).
2. Map each logical module name to a **directory** of `.clrs` files:

```toml
module = "clrs.io/local"

[paths]
"Clrs.Sorting" = "lib/sorting"

[require]
"Clrs.Sorting" = "local"
```

Optional v2 tables (same TOML file):

- **`[replace]`** — override a `[paths]` entry (Go-style `replace`).
- **`[exclude]`** — block importing a module path even if it is mapped.
- **`import Clrs.Sorting as Sort`** — qualified calls such as `Sort.MergeSort(A, 1, n)` reach the imported module even when a local definition shadows the unqualified name.

3. Every file in a mapped directory must declare the **same** `Module` line as the map key (`Module Clrs.Sorting` for `"Clrs.Sorting" = "lib/sorting"`).
4. In your entry file, **`import`** the modules you need (after `Module`, before any procedure). The compiler loads **all** `*.clrs` in each mapped directory, follows **transitive** imports, and rejects **cycles**.

**Example entry file** (`cmd/demo/main.clrs` — create locally if you like):

```text
Module demo

import Clrs.Sorting

Run(A)
	InsertionSort(A)
	return A
```

Run with only the entry path:

```bash
python3 -m clrs run cmd/demo/main.clrs -- 'Run([5, 2, 4, 6, 1, 3])'
```

`compile` and `pack` resolve the same import graph from the entry file.

More detail: [docs/planning/module-import-and-pack.md](docs/planning/module-import-and-pack.md).

---

Package layout: [docs/project-layout.md](docs/project-layout.md). Milestones and gates: [docs/milestones.md](docs/milestones.md).
