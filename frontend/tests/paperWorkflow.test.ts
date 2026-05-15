import assert from "node:assert/strict";
import test from "node:test";

import { getAcquireActionState, isPaperParsed, matchesLibraryFilter } from "../src/lib/paperWorkflow.js";

type TestPaper = Parameters<typeof getAcquireActionState>[0] & {
  paper_id: string;
  title: string;
  slug: string;
  status: string;
  domain: string;
  area: string;
  topic: string;
  year: number | null;
  venue: string;
  doi: string;
  tags: string[];
  path: string;
  refined_path: string;
  images_path: string;
  metadata_path: string;
  metadata_json_path: string;
  state_path: string;
  parsed_text_path: string;
  parsed_sections_path: string;
  pdf_analysis_path: string;
  note_status: string;
  read_status: string;
  refined_review_status: string;
  classification_status: string;
  rejected: boolean;
  error: string;
  updated_at: string;
};

function createPaper(overrides: Partial<TestPaper> = {}): TestPaper {
  return {
    paper_id: "Acquire__curated__sample",
    title: "Sample Paper",
    slug: "sample-paper",
    stage: "acquire",
    status: "parse-pending",
    asset_status: "pdf_ready",
    review_status: "pending",
    domain: "Speech",
    area: "TTS",
    topic: "Control",
    year: 2026,
    venue: "AAAI",
    doi: "",
    tags: ["paper"],
    path: "C:/tmp/Sample",
    paper_path: "C:/tmp/Sample/paper.pdf",
    note_path: "",
    refined_path: "",
    images_path: "",
    metadata_path: "",
    metadata_json_path: "",
    state_path: "",
    parsed_text_path: "",
    parsed_sections_path: "",
    pdf_analysis_path: "",
    parser_status: "not_started",
    note_status: "missing",
    parser_artifacts: {
      text_path: "",
      sections_path: "",
      refined_path: "",
    },
    capabilities: {
      parse: true,
      accept: false,
      generate_note: true,
      delete: true,
    },
    read_status: "unread",
    refined_review_status: "pending",
    classification_status: "pending",
    rejected: false,
    error: "",
    updated_at: "2026-05-15T00:00:00Z",
    ...overrides,
  } satisfies TestPaper;
}

test("capabilities drive acquire actions", () => {
  const paper = createPaper({
    parser_status: "failed",
    capabilities: {
      parse: true,
      accept: true,
      generate_note: false,
      delete: true,
    },
  });

  const state = getAcquireActionState(paper);

  assert.equal(state.parseLabel, "Retry Parse");
  assert.equal(state.canParse, true);
  assert.equal(state.canAccept, true);
  assert.equal(state.canGenerateNote, false);
  assert.equal(state.canDelete, true);
});

test("parsed state does not depend on refined artifact path", () => {
  const paper = createPaper({
    parser_status: "parsed",
    parser_artifacts: {
      text_path: "C:/tmp/Sample/parsed/text.md",
      sections_path: "C:/tmp/Sample/parsed/sections.json",
      refined_path: "",
    },
  });

  const state = getAcquireActionState(paper);

  assert.equal(isPaperParsed(paper), true);
  assert.equal(state.parsed, true);
  assert.equal(state.hasRefinedArtifact, false);
});

test("library filters use new workflow fields instead of compat status", () => {
  const pendingReviewPaper = createPaper({
    stage: "library",
    status: "parse-pending",
    parser_status: "parsed",
    review_status: "pending",
  });
  const acceptedPaper = createPaper({
    stage: "library",
    status: "needs-review",
    parser_status: "parsed",
    review_status: "accepted",
  });

  assert.equal(matchesLibraryFilter(pendingReviewPaper, "pending-review"), true);
  assert.equal(matchesLibraryFilter(pendingReviewPaper, "accepted"), false);
  assert.equal(matchesLibraryFilter(acceptedPaper, "accepted"), true);
  assert.equal(matchesLibraryFilter(acceptedPaper, "pending-review"), false);
});
