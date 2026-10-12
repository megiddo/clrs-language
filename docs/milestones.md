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
