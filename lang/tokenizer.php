<?php

$clrs_tok = new ClrsTokenizer();
$clrs_tok->OpenFile($argv[1]);
$clrs_tok->Tokenize();

print_r($clrs_tok->tokens);

class Clrs {
  static $DELIMITERS = " ←↔▷∞⌊⌋⌈⌉(){}<>=,[].";
  static function RegexDelimiters() {
    return '/[' . mb_substr(addcslashes(Clrs::$DELIMITERS, "[](){}."), 1) . ']/u';
  }
}

class ClrsTokenizer {

  var $lines;
  var $tokens;

  function OpenFile($file_name) {
    $this->lines = file($file_name);
  }

  function FromString($string) {
    $this->lines = explode("\n", $string);
  }

  function Tokenize() {
    $lines = $this->lines;
    $lines[count($lines)-1] .= "\n";
    $lines[count($lines)] = "";

    $depth = 0;
    $line_idx = 0;

    $processed_lines[] = rtrim($lines[0], "\n");
    for ($l = 1; $l < count($lines); $l++) {
      $processed_lines[] = $line = rtrim($lines[$l], "\n");
      $lastdepth = $depth;
      $depth = $this->IndentLevel($line);
      if ($depth > $lastdepth) {
        $processed_lines[$l - 1] .= " {";
      } else if ($depth < $lastdepth) {
        $processed_lines[$l] = $this->CloseBraces($lastdepth - 1, $lastdepth - $depth) . " " . ltrim($processed_lines[$l]);
      }
    }

    echo implode("\n", $processed_lines) . "\n";

    $contents = preg_replace("/\s+/", " ", implode("", $processed_lines));

    $delimiters = Clrs::$DELIMITERS; //" ←↔▷∞⌊⌋⌈⌉(){}<>=,[]";
    $tokens = [];
    while ($token = strtok($contents, $delimiters)) {
      $tokens[] = $token;
      $contents = substr($contents, strlen($token));
      for ($c = 0; $c < mb_strlen($contents); $c++) {
        if (mb_substr($contents, $c, 1) == " ") continue;
        if (preg_match(Clrs::RegexDelimiters(), mb_substr($contents, $c, 1), $matches)) {
          $match = mb_substr($contents, $c, 1);
          $tokens[] = $match;
        } else {
          $contents = mb_substr($contents, $c);
          break;
        }
      }
    }

    $this->tokens = $tokens;

    return true;
  }

  function CloseBraces($depth, $levels) {
    $closes = "";
    for ($l = 0; $l < $levels; $l++) {
      $closes .= str_repeat($this->indentor, $depth) . "}";
      $depth--;
      if ($l < $levels - 1) {
        $closes .= "\n";
      }
    }
    return $closes;
  }

  var $indentor = null;
  function IndentorMatches($ident) {
    if (is_null($this->indentor)) $this->indentor = $ident;
    return $this->indentor == $ident;
  }

  function IndentLevel($line) {
    $level = 0;
    for ($l = 0; $l < mb_strlen($line); $l++) {
      if (mb_substr($line, $l, 1) == "\t" && $this->IndentorMatches("\t")) {
        $level++;
      } else if (mb_strlen($line) > ($l + 1) && mb_substr($line, $l, 2) == "  " && $this->IndentorMatches("  ")) { 
        $l++; $level++;
      } else if (mb_substr($line, $l, 1) == "\t" && !$this->IndentorMatches("\t")) {
        die("You must use consistent indentation. This file is a double-space file.");
      } else if (mb_strlen($line) > ($l + 1) && mb_substr($line, $l, 2) == "  " && !$this->IndentorMatches("  ")) {
        die("You must use consistent indentation. This file is a tabbed file.");
      } else {
        return $level;
      }
    }
    return 0;
  }
}

class ClrsAst {
  var $ast = [];
  var $tokens;

  /*
    Program := File File
    File := File File
    File := Statement
    Statement := Expression Function EOL
    Expression := Expression 
  */

  function TokensToAst($tokens) {
    $this->tokens = $tokens;
  }
}

class AstNode {
  var $left;
  var $right;
  var $sourceLine;
}