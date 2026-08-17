import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const demo = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFile(resolve(demo, path), "utf8");
const app = await read("app.js");
const coreSource = await read("pilot-core.js");
const html = await read("index.html");
const readme = await read("README.md");

assert.match(html, /connect-src 'none'/);
assert.match(html, /Browser-local pilot · encrypted fictional data · no network connection/);
assert.ok(html.indexOf("pilot-core.js") < html.indexOf("app.js"));
assert.doesNotMatch(`${app}\n${coreSource}`, /\b(fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(/);
assert.doesNotMatch(`${app}\n${coreSource}`, /postgresql?:|DATABASE_URL|indexedDB/);
assert.doesNotMatch(app, /localStorage\.setItem\([^,]+,\s*JSON\.stringify\(state\)/);
assert.match(coreSource, /AES-GCM/);
assert.match(coreSource, /PBKDF2/);
assert.match(app, /const openChecks = checks\.filter\(\(check\) => !check\.ok\)/);
assert.match(app, /report-final-controls/);
assert.match(readme, /Calendar year 2025/);

const samples = await readdir(resolve(demo, "sample"));
assert.ok(samples.includes("fictional-organisation-2025.csv"));
assert.ok(samples.includes("fictional-scope-1-2025.csv"));
assert.ok(samples.includes("fictional-scope-2-2025.csv"));
assert.ok(samples.includes("fictional-scope-3-2025.csv"));
for (const filename of samples.filter((name) => name.endsWith(".csv"))) {
  const content = await read(`sample/${filename}`);
  const lines = content.trim().split(/\r?\n/);
  assert.ok(lines.length >= 2, `${filename} has a heading and a data row`);
  assert.equal(new Set(lines[0].split(",")).size, lines[0].split(",").length, `${filename} headings are unique`);
  assert.doesNotMatch(content, /@|\+44|https?:\/\//, `${filename} contains no contact or URL-like value`);
}

const json = JSON.parse(await read("sample/new-era-group-activity-data.json"));
assert.ok(Array.isArray(json.records) && json.records.length > 0);
assert.ok(json.records.every((row) => row.calculation_method_id && row.activity_value && row.evidence_reference));

for (const scope of [1, 2, 3]) {
  assert.match(app, new RegExp(`data-scope-download`));
  assert.match(coreSource, new RegExp(`scope${scope}\\.`));
}

console.log("pilot-static: CSP, network/database, templates, CSV/JSON and PII-shape checks passed");
