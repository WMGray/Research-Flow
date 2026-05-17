import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const discoverPagePath = path.resolve(process.cwd(), "src/pages/WorkflowPage.tsx");
const discoverFiltersPath = path.resolve(process.cwd(), "src/components/discover/DiscoverFilters.tsx");
const libraryPagePath = path.resolve(process.cwd(), "src/pages/LibraryPage.tsx");
const archivePagePath = path.resolve(process.cwd(), "src/pages/ArchivePage.tsx");
const paperWorkflowPath = path.resolve(process.cwd(), "src/lib/paperWorkflow.ts");

test("discover page exposes card-flow candidate decisions without manual ingest", () => {
  const source = fs.readFileSync(discoverPagePath, "utf-8");

  assert.equal(source.includes("Add Curated Paper"), false);
  assert.equal(source.includes("transferPaper"), false);
  assert.equal(source.includes("ingestPaper("), false);
  assert.equal(source.includes("migratePaper("), false);
  assert.match(source, /收录/);
  assert.match(source, /剔除/);
  assert.match(source, /CandidateCard/);
  assert.equal(source.includes("ResponsivePaperInspector"), false);
  assert.match(source, /pendingCandidates/);
});

test("discover filters only expose batch and score controls", () => {
  const source = fs.readFileSync(discoverFiltersPath, "utf-8");

  assert.match(source, /batchId/);
  assert.match(source, /minScore/);
  assert.match(source, /maxScore/);
  assert.equal(source.includes("source"), false);
  assert.equal(source.includes("year"), false);
  assert.equal(source.includes("venue"), false);
  assert.equal(source.includes("domain"), false);
  assert.equal(source.includes("status"), false);
  assert.equal(source.includes("query"), false);
});

test("library uses inspector panel instead of row detail buttons", () => {
  const source = fs.readFileSync(libraryPagePath, "utf-8");

  assert.equal(source.includes("library-detail-actions"), false);
  assert.equal(source.includes("to={`/library/"), false);
  assert.match(source, /ResponsivePaperInspector/);
  assert.match(source, /Title/);
  assert.match(source, /Venue/);
  assert.match(source, /Updated/);
  assert.match(source, /selectedPaperId/);
  assert.match(source, /onParsePdf/);
  assert.match(source, /onGenerateNote/);
  assert.match(source, /onCreateFolder/);
  assert.match(source, /onDropPaper/);
  assert.equal(source.includes("ClassificationSelect"), false);
  assert.equal(source.includes("filterPapersByClassification"), false);
});

test("archive keeps restore action frontend-only", () => {
  const source = fs.readFileSync(archivePagePath, "utf-8");

  assert.equal(source.includes("restorePaper"), false);
  assert.equal(source.includes("/restore"), false);
  assert.match(source, /恢复动作暂不可用/);
});

test("acquire actions stay capability-driven", () => {
  const source = fs.readFileSync(paperWorkflowPath, "utf-8");

  assert.match(source, /canGenerateNote:\s*paper\.capabilities\.generate_note/);
  assert.match(source, /canParse:\s*paper\.capabilities\.parse/);
  assert.match(source, /canAccept:\s*paper\.capabilities\.accept/);
  assert.match(source, /canDelete:\s*paper\.capabilities\.delete/);
});
