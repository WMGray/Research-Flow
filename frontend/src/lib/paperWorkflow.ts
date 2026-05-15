export type LibraryFilter = "all" | "accepted" | "pending-review" | "missing-pdf" | "parse-failed" | "parsed";

type PaperCapabilities = {
  parse: boolean;
  accept: boolean;
  generate_note: boolean;
  delete: boolean;
};

type ParserArtifacts = {
  text_path: string;
  sections_path: string;
  refined_path: string;
};

type PaperWorkflowSnapshot = {
  stage: string;
  asset_status: string;
  parser_status: string;
  review_status: string;
  note_path: string;
  paper_path: string;
  capabilities: PaperCapabilities;
  parser_artifacts: ParserArtifacts;
};

export function isPaperParsed(paper: Pick<PaperWorkflowSnapshot, "parser_status">): boolean {
  return paper.parser_status === "parsed";
}

export function isGate2ReviewPaper(paper: Pick<PaperWorkflowSnapshot, "stage" | "parser_status" | "review_status">): boolean {
  return paper.stage === "acquire" && isPaperParsed(paper) && paper.review_status === "pending";
}

export function matchesLibraryFilter(paper: Pick<PaperWorkflowSnapshot, "asset_status" | "parser_status" | "review_status">, filter: LibraryFilter): boolean {
  switch (filter) {
    case "accepted":
      return paper.review_status === "accepted";
    case "pending-review":
      return paper.review_status === "pending" && isPaperParsed(paper);
    case "missing-pdf":
      return paper.asset_status === "missing_pdf";
    case "parse-failed":
      return paper.parser_status === "failed";
    case "parsed":
      return isPaperParsed(paper);
    default:
      return true;
  }
}

export function getAcquireActionState(paper: PaperWorkflowSnapshot) {
  return {
    hasNote: Boolean(paper.note_path),
    hasPdf: Boolean(paper.paper_path),
    parseLabel: paper.parser_status === "failed" ? "Retry Parse" : "Parse",
    parseIcon: paper.parser_status === "failed" ? "alert" : "play",
    canGenerateNote: paper.capabilities.generate_note,
    canParse: paper.capabilities.parse,
    canAccept: paper.capabilities.accept,
    canDelete: paper.capabilities.delete,
    parsed: isPaperParsed(paper),
    hasRefinedArtifact: Boolean(paper.parser_artifacts.refined_path),
  } as const;
}
