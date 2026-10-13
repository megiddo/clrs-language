"""The .clrsa TextMate grammar highlights every opcode and directive the loader reads."""

import json
import re
import unittest
from pathlib import Path

from clrs.bytecode import COMPARISON_NAMES
from clrs.bytecode import Opcode
from clrs.bytecode.loader import DIRECTIVES

VSCODE = Path(__file__).resolve().parents[1] / "editors" / "vscode"


class ClrsaGrammarTest(unittest.TestCase):
    def setUp(self) -> None:
        self.grammar = json.loads((VSCODE / "syntaxes" / "clrsa.tmLanguage.json").read_text())
        self.repository = self.grammar["repository"]

    def test_registered_for_clrsa_files(self) -> None:
        package = json.loads((VSCODE / "package.json").read_text())
        languages = {entry["id"]: entry for entry in package["contributes"]["languages"]}
        self.assertEqual(languages["clrsa"]["extensions"], [".clrsa"])
        grammars = {entry["language"]: entry for entry in package["contributes"]["grammars"]}
        self.assertEqual(grammars["clrsa"]["scopeName"], self.grammar["scopeName"])
        self.assertTrue((VSCODE / grammars["clrsa"]["path"]).is_file())

    def test_every_opcode_is_highlighted(self) -> None:
        begin = re.compile(self.repository["instruction"]["begin"])
        for opcode in Opcode:
            with self.subTest(opcode=opcode.value):
                self.assertIsNotNone(begin.match(f"{opcode.value} x"))
        self.assertIsNone(begin.match("LOADX"))

    def test_jumps_are_scoped_apart_from_other_opcodes(self) -> None:
        begin = re.compile(self.repository["instruction"]["begin"])
        self.assertEqual(begin.match("JUMP_IF_FALSE L").group(1), "JUMP_IF_FALSE")
        self.assertEqual(begin.match("CMP le").group(2), "CMP")

    def test_every_directive_label_comment_and_comparison(self) -> None:
        directive = re.compile(self.repository["directive"]["match"])
        for name in DIRECTIVES:
            with self.subTest(directive=name):
                self.assertEqual(directive.match(f"{name} x").group(1), name)
        label = re.compile(self.repository["label"]["match"])
        self.assertEqual(label.match("L_for_end_1:").group(1), "L_for_end_1")
        self.assertIsNone(label.match("CONST 1"))
        comment = re.compile(self.repository["comment"]["match"])
        self.assertEqual(comment.search("RET ▷ done").group(0), "▷ done")
        comparison = re.compile(self.repository["comparison"]["match"])
        for name in COMPARISON_NAMES.values():
            self.assertIsNotNone(comparison.fullmatch(name))

    def test_param_is_a_directive_with_a_named_slot(self) -> None:
        directive = re.compile(self.repository["directive"]["match"])
        match = directive.match("  .param key ▷ first slot")
        self.assertEqual((match.group(1), match.group(2).strip()), (".param", "key"))
        self.assertIsNone(directive.match(".parameter x"))
        self.assertIn(".param", DIRECTIVES)


if __name__ == "__main__":
    unittest.main()
