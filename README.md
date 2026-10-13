# clrs-language

Yak shave to implement CLRS pseudocode as a language.

Run a driver over the example modules:

```bash
python3 -m clrs run examples/insertion-sort.clrs -- 'A ← [5, 2, 4, 6, 1, 3]; InsertionSort(A); A'
```

Compile to textual bytecode (stdout, or `-o`):

```bash
python3 -m clrs compile examples/insertion-sort.clrs -o build/insertion-sort.clrsa
python3 -m clrs compile examples/heap.clrs examples/heapsort.clrs -o build/heapsort.clrsa
```

Package layout: [docs/project-layout.md](docs/project-layout.md). Import and packed-executable plans: [docs/planning/module-import-and-pack.md](docs/planning/module-import-and-pack.md). Milestones and gates: [docs/milestones.md](docs/milestones.md).
