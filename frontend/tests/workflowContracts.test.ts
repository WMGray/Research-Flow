import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const workflowPanelsPath = path.resolve(process.cwd(), "src/components/workflow/WorkflowPanels.tsx");

test("acquire workflow no longer exposes manual curated ingest entry", () => {
  const source = fs.readFileSync(workflowPanelsPath, "utf-8");

  assert.equal(source.includes("Add Curated Paper"), false);
  assert.equal(source.includes("transferPaper"), false);
  assert.equal(source.includes("ingestPaper("), false);
  assert.equal(source.includes("migratePaper("), false);
  assert.equal(source.includes("Detail"), false);
});
