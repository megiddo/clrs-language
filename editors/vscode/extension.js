"use strict";

const path = require("path");
const { spawn } = require("child_process");
const vscode = require("vscode");
const { aliasReplacements } = require("./aliases");

const repoRoot = path.resolve(__dirname, "..", "..");
const generation = new Map();
let applying = false;
let pythonWarned = false;

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection("clrs");
  const lintSoon = debounce((document) => lintDocument(document, diagnostics), 200);

  context.subscriptions.push(diagnostics);
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((document) => {
      if (document.languageId === "clrs") lintSoon(document);
    }),
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (applying || event.document.languageId !== "clrs") return;
      if (rewrite(event.document, lintSoon)) return;
      lintSoon(event.document);
    }),
    vscode.workspace.onDidCloseTextDocument((document) => {
      diagnostics.delete(document.uri);
    }),
    vscode.commands.registerCommand("clrs.rewriteAliases", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document.languageId !== "clrs") return;
      rewrite(editor.document, lintSoon);
    })
  );

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === "clrs") lintSoon(document);
  }
}

function rewrite(document, after) {
  const edits = aliasReplacements(document.getText()).map((replacement) =>
    vscode.TextEdit.replace(
      new vscode.Range(
        document.positionAt(replacement.start),
        document.positionAt(replacement.end)
      ),
      replacement.insert
    )
  );
  if (edits.length === 0) return false;
  const edit = new vscode.WorkspaceEdit();
  edit.set(document.uri, edits);
  applying = true;
  vscode.workspace.applyEdit(edit).finally(() => {
    applying = false;
    after(document);
  });
  return true;
}

function lintDocument(document, diagnostics) {
  const key = document.uri.toString();
  const id = (generation.get(key) || 0) + 1;
  generation.set(key, id);
  const child = spawn("python3", ["-m", "clrs_lint", "--json"], { cwd: repoRoot });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => {
    stdout += chunk;
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  child.stdin.write(document.getText());
  child.stdin.end();
  child.on("error", () => warnPython(stderr));
  child.on("close", () => {
    if (generation.get(key) !== id) return;
    let items;
    try {
      items = JSON.parse(stdout || "[]");
    } catch (err) {
      warnPython(stderr || String(err));
      return;
    }
    diagnostics.set(
      document.uri,
      items.map(
        (item) =>
          new vscode.Diagnostic(
            new vscode.Range(item.line - 1, item.column - 1, item.endLine - 1, item.endColumn - 1),
            item.message,
            vscode.DiagnosticSeverity.Error
          )
      )
    );
  });
}

function warnPython(detail) {
  if (pythonWarned) return;
  pythonWarned = true;
  vscode.window.showWarningMessage(
    "CLRS linter could not run python3 -m clrs_lint. " + (detail || "")
  );
}

function debounce(fn, wait) {
  const timers = new Map();
  return (document) => {
    const key = document.uri.toString();
    clearTimeout(timers.get(key));
    timers.set(
      key,
      setTimeout(() => fn(document), wait)
    );
  };
}

function deactivate() {}

module.exports = { activate, deactivate };
