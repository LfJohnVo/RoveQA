#!/usr/bin/env node
// Turn a RoveQA CLI envelope into a JUnit report, without inventing a result.
//
//   roveqa run wait "$RUN" --timeout 15m --output json > verdict.json; echo $? > code
//   node verdict-to-junit.mjs verdict.json "$(cat code)" > junit.xml
//
// The one rule: **this never decides the outcome**. It exits with the code the CLI gave
// it. A CI adapter that reported "tests ran" while the run had timed out would be worse
// than no adapter — it would make a green pipeline out of a question nobody answered.
import { readFileSync } from "node:fs";

const [, , envelopePath, cliExitCode] = process.argv;
if (!envelopePath) {
  process.stderr.write("usage: verdict-to-junit.mjs <envelope.json> [cli-exit-code]\n");
  process.exit(64);
}

const envelope = JSON.parse(readFileSync(envelopePath, "utf8"));
const exitCode = Number.parseInt(cliExitCode ?? "0", 10) || 0;

function escapeXml(value) {
  return String(value).replace(/[<>&"']/g, (character) =>
    ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[character],
  );
}

// Three shapes, three meanings, and the difference matters more than the XML does.
let name = "roveqa";
let body = "";
let failures = 0;
let errors = 0;

if (envelope.error) {
  // The run has no verdict. `WAIT_TIMEOUT` in particular means it is still going: a
  // report claiming failure would be as wrong as one claiming success.
  name = `roveqa ${envelope.error.code}`;
  errors = 1;
  body =
    `    <error type="${escapeXml(envelope.error.code)}" ` +
    `message="${escapeXml(envelope.error.message)}">` +
    `${escapeXml(envelope.error.next_action ?? "")}</error>`;
} else {
  const verdict = envelope.data?.verdict ?? "unknown";
  name = `roveqa run ${envelope.data?.run_id ?? "unknown"}`;
  if (verdict !== "passed") {
    // `failed` is a defect; `blocked` and `inconclusive` are the run saying it could not
    // answer. None of them are a pass, and none of them are the same thing.
    failures = 1;
    body = `    <failure type="${escapeXml(verdict)}">verdict: ${escapeXml(verdict)}</failure>`;
  }
}

const testcase = body
  ? `  <testcase name="${escapeXml(name)}">\n${body}\n  </testcase>`
  : `  <testcase name="${escapeXml(name)}"/>`;

process.stdout.write(
  `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<testsuite name="roveqa" tests="1" failures="${failures}" errors="${errors}">\n` +
    `${testcase}\n</testsuite>\n`,
);

// The CLI's code, unchanged. 0 pass, 1 terminal non-pass, 7 the client stopped waiting.
process.exit(exitCode);
