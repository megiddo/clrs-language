"use strict";

// Longest alias first. The caret in |^ and ^| is U+005E, not a backtick.
// ←> exists only so typing <-> one character at a time still becomes ↔
// after <- has already been rewritten to ←.
const ALIASES = [
  ["<->", "↔"],
  ["←>", "↔"],
  [".Inf", "∞"],
  ["<-", "←"],
  ["<=", "≤"],
  [">=", "≥"],
  ["!=", "≠"],
  ["|>", "▷"],
  ["|.", "⌊"],
  [".|", "⌋"],
  ["|^", "⌈"],
  ["^|", "⌉"],
];

function aliasReplacements(text) {
  const replacements = [];
  let index = 0;
  while (index < text.length) {
    const pair = ALIASES.find(([from]) => text.startsWith(from, index));
    if (!pair) {
      index += 1;
      continue;
    }
    const [from, to] = pair;
    replacements.push({ start: index, end: index + from.length, insert: to });
    index += from.length;
  }
  return replacements;
}

module.exports = { ALIASES, aliasReplacements };
