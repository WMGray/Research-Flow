import assert from "node:assert/strict";
import test from "node:test";

import type { CandidateRecord } from "../src/lib/api.js";
import { buildClassificationOptions, derivePaperStatus, filterCandidates, filterPapersByClassification, getClassificationChoices } from "../src/lib/libraryView.js";

type TestPaper = {
  stage: string;
  asset_status: string;
  parser_status: string;
  review_status: string;
  note_path: string;
  paper_path: string;
  capabilities: {
    parse: boolean;
    accept: boolean;
    generate_note: boolean;
    review_refined: boolean;
    review_note: boolean;
    delete: boolean;
  };
  parser_artifacts: {
    text_path: string;
    sections_path: string;
    refined_path: string;
  };
  paper_id: string;
  title: string;
  slug: string;
  authors: string[];
  abstract: string;
  summary: string;
  url: string;
  arxiv_id: string;
  starred: boolean;
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
    authors: [],
    abstract: "",
    summary: "",
    url: "",
    arxiv_id: "",
    starred: false,
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
    abstract: "",
    url: "",
    doi: "",
    arxiv_id: "",
    pdf_url: "",
    landing_status: "downloaded",
    result_path: "C:/tmp/candidate",
    updated_at: "2026-05-15T00:00:00Z",
    ...overrides,
  };
}

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
