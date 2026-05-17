import assert from "node:assert/strict";
import test from "node:test";

import type { CandidateRecord } from "../src/lib/api.js";
import { buildClassificationOptions, derivePaperStatus, filterCandidates, filterPapersByClassification, getClassificationChoices } from "../src/lib/libraryView.js";
import { getAcquireActionState, isPaperParsed, matchesLibraryFilter } from "../src/lib/paperWorkflow.js";

type TestPaper = Parameters<typeof getAcquireActionState>[0] & {
  paper_id: string;
  title: string;
  slug: string;
  status: string;
  workflow_status: string;
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
  events_path: string;
  parsed_text_path: string;
  parsed_sections_path: string;
  pdf_analysis_path: string;
  note_status: string;
  note_review_status: string;
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
    workflow_status: "not_started",
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
    events_path: "",
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
      review_refined: false,
      review_note: false,
      delete: true,
    },
    read_status: "unread",
    refined_review_status: "pending",
    note_review_status: "missing",
    classification_status: "pending",
    rejected: false,
    error: "",
    updated_at: "2026-05-15T00:00:00Z",
    ...overrides,
  } satisfies TestPaper;
}

function createCandidate(overrides: Partial<CandidateRecord> = {}): CandidateRecord {
  return {
    candidate_id: "P001",
    batch_id: "batch-a",
    title: "Candidate Paper",
    authors: ["A. Researcher"],
    year: 2026,
    venue: "AAAI",
    decision: "pending",
    source_type: "arxiv",
    collection_role: "Core",
    paper_type: "paper",
    quality: 80,
    relevance: 90,
    recommendation_reason: "Relevant.",
    landing_status: "downloaded",
    result_path: "C:/tmp/candidate",
    updated_at: "2026-05-15T00:00:00Z",
    ...overrides,
  };
}

test("capabilities drive acquire actions", () => {
  const paper = createPaper({
    parser_status: "failed",
    capabilities: {
      parse: true,
      accept: true,
      generate_note: false,
      review_refined: true,
      review_note: false,
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

test("derive paper status prefers workflow_status", () => {
  const paper = createPaper({
    workflow_status: "note_review_pending",
    parser_status: "parsed",
    note_path: "C:/tmp/Sample/note.md",
    status: "processed",
  });

  assert.equal(derivePaperStatus(paper), "note_review_pending");
});

test("candidate filters only use batch and score range", () => {
  const candidates = [
    createCandidate({ candidate_id: "P001", batch_id: "batch-a", source_type: "arxiv", quality: 80, relevance: 90 }),
    createCandidate({ candidate_id: "P002", batch_id: "batch-a", source_type: "local", quality: 30, relevance: 40 }),
    createCandidate({ candidate_id: "P003", batch_id: "batch-b", source_type: "arxiv", quality: 90, relevance: 94 }),
  ];

  const filtered = filterCandidates(candidates, { batchId: "batch-a", minScore: 70, maxScore: 100 });

  assert.deepEqual(filtered.map((candidate) => candidate.candidate_id), ["P001"]);
});

test("classification options narrow area and topic choices", () => {
  const papers = [
    createPaper({ paper_id: "p1", domain: "Vision", area: "Video", topic: "Action Anticipation" }),
    createPaper({ paper_id: "p2", domain: "Vision", area: "Detection", topic: "Object Detection" }),
    createPaper({ paper_id: "p3", domain: "Speech", area: "TTS", topic: "Voice Conversion" }),
  ];
  const options = buildClassificationOptions(papers);
  const choices = getClassificationChoices(options, { domain: "Vision", area: "Video", topic: "" });
  const filtered = filterPapersByClassification(papers, { domain: "Vision", area: "Video", topic: "all" });

  assert.deepEqual(choices.areas, ["Detection", "Video"]);
  assert.deepEqual(choices.topics, ["Action Anticipation"]);
  assert.deepEqual(filtered.map((paper) => paper.paper_id), ["p1"]);
});
