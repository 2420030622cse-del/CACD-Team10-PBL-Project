import assert from "node:assert/strict";
import test from "node:test";
import { compileMiniLang } from "../static/js/minilang.js";

test("respects arithmetic precedence and folds constant expressions", () => {
  const result = compileMiniLang("let answer = 2 + 3 * 4; print(answer);");
  assert.equal(result.error, null);
  assert.deepEqual(result.output, ["14"]);
  assert.ok(result.tac.length > result.optimizedTac.length);
  assert.equal(result.stats.folded, 2);
});

test("executes loops, branches, string concatenation, and logical expressions", () => {
  const result = compileMiniLang(`
    let total = 0;
    let i = 0;
    while (i < 4 && true) { total = total + i; i = i + 1; }
    if (total == 6) { print("Mini" + "Lang"); } else { print("wrong"); }
  `);
  assert.equal(result.error, null);
  assert.deepEqual(result.output, ["MiniLang"]);
});

test("enforces block scope while allowing assignment to outer variables", () => {
  const result = compileMiniLang("let value = 1; { let hidden = 2; value = 3; } print(value);");
  assert.equal(result.error, null);
  assert.deepEqual(result.output, ["3"]);
  const inaccessible = compileMiniLang("{ let hidden = 2; } print(hidden);");
  assert.equal(inaccessible.error?.phase, "Semantic");
});

test("reports lexical, syntax, and semantic errors with their compiler phase", () => {
  assert.equal(compileMiniLang("let x = @;").error?.phase, "Lexical");
  assert.equal(compileMiniLang("let x = 1").error?.phase, "Syntax");
  assert.equal(compileMiniLang("let x = true + 1;").error?.phase, "Semantic");
});

test("preserves escaped token text and decimal types through optimization", () => {
  const result = compileMiniLang('let label = "line\\ntext"; let value = 1.0 + 2.0; print(value);');
  assert.equal(result.error, null);
  assert.equal(result.tokens.find(token => token.kind === "string")?.lexeme, '"line\\ntext"');
  assert.equal(result.ast?.[1]?.kind, "declaration");
  assert.equal(result.optimizedAst?.[1]?.kind, "declaration");
  assert.deepEqual(result.output, ["3"]);
});

test("reports execution failures and stops non-terminating loops", () => {
  assert.equal(compileMiniLang("print(1 / 0);").error?.phase, "Execution");
  const loop = compileMiniLang("while (true) { let step = 1; }");
  assert.match(loop.error?.message ?? "", /25,000 statements/);
});