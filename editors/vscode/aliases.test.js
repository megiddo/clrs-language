"use strict";

const assert = require("assert");
const { ALIASES, aliasReplacements } = require("./aliases");

function rewritten(text) {
  let out = "";
  let index = 0;
  for (const replacement of aliasReplacements(text)) {
    out += text.slice(index, replacement.start) + replacement.insert;
    index = replacement.end;
  }
  return out + text.slice(index);
}

assert.deepStrictEqual(rewritten("<-"), "←");
assert.deepStrictEqual(rewritten("<->"), "↔");
assert.deepStrictEqual(rewritten("←>"), "↔");
assert.deepStrictEqual(rewritten("|> comment"), "▷ comment");
assert.deepStrictEqual(rewritten("|.x.|"), "⌊x⌋");
assert.deepStrictEqual(rewritten("|^x^|"), "⌈x⌉");
assert.deepStrictEqual(rewritten(".Inf"), "∞");
assert.deepStrictEqual(rewritten("<="), "≤");
assert.deepStrictEqual(rewritten("`"), "`");
assert.ok(ALIASES.some(([from]) => from === "|^"));
assert.ok(!ALIASES.some(([from]) => from.includes("`")));

console.log("aliases ok");
