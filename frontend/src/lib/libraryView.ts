import type { CandidateRecord, PaperRecord } from "@/lib/api";

export type SortDirection = "asc" | "desc";
export type SortKey = "title" | "venue" | "year" | "tags" | "status" | "updated";
export type TreeLevel = "all" | "domain" | "area" | "topic" | "system";
export type MissingField = "Domain" | "Area" | "Topic" | "Tags";

export type SortState = {
  key: SortKey;
  direction: SortDirection;
};

export type ClassificationFilterState = {
  domain: string;
  area: string;
  topic: string;
};

export type ClassificationTarget = {
  domain: string;
  area: string;
  topic: string;
};

export type ClassificationOptionSet = {
  domains: string[];
  areas: string[];
  topics: string[];
  areasByDomain: Record<string, string[]>;
  topicsByDomainArea: Record<string, string[]>;
};

export type ClassificationTreeNode = {
  id: string;
  label: string;
  level: TreeLevel;
  count: number;
  target: ClassificationTarget;
  children: ClassificationTreeNode[];
  system?: "recent" | "to_read" | "unclassified";
};

export type PaperListItemView = PaperRecord & {
  displayStatus: string;
  missingFields: MissingField[];
};

export type LibraryOverviewStats = {
  total: number;
  unclassified: number;
  missingPdf: number;
  parsed: number;
  parseFailed: number;
  notes: number;
  thisWeek: number;
  recentParseSuccess: number;
};

export const EMPTY_TARGET: ClassificationTarget = {
  domain: "",
  area: "",
  topic: "",
};

export const DOMAIN_TREE_SEEDS: ClassificationTreeNode[] = [
  systemNode("recent", "最近阅读"),
  systemNode("to_read", "待读"),
  domainSeed("度量学习"),
  domainSeed("端侧设备部署"),
  {
    ...domainSeed("多模态大模型"),
    children: [topicSeed("多模态大模型", "模型压缩"), topicSeed("多模态大模型", "世界模型"), topicSeed("多模态大模型", "MLLM")],
  },
  domainSeed("人机交互"),
  domainSeed("少样本学习"),
  domainSeed("增量学习"),
  domainSeed("Action Prediction"),
  domainSeed("Data Augmentation"),
  domainSeed("Environment Understanding"),
  domainSeed("HOI"),
  domainSeed("Representation Learning"),
  systemNode("unclassified", "未分类"),
];

export function isReviewedLibraryPaper(paper: PaperRecord): boolean {
  return paper.stage === "library" && paper.review_status === "accepted";
}

export function isUncategorizedPaper(paper: Pick<PaperRecord, "domain" | "area" | "topic" | "tags">): boolean {
  return missingFieldsForPaper(paper).length > 0;
}

export function missingFieldsForPaper(paper: Pick<PaperRecord, "domain" | "area" | "topic" | "tags">): MissingField[] {
  const fields: MissingField[] = [];
  if (!cleanClassification(paper.domain)) fields.push("Domain");
  if (!cleanClassification(paper.area)) fields.push("Area");
  if (!cleanClassification(paper.topic)) fields.push("Topic");
  if (!paper.tags || paper.tags.length === 0) fields.push("Tags");
  return fields;
}

export function buildClassificationTree(papers: PaperRecord[]): ClassificationTreeNode {
  const root: ClassificationTreeNode = {
    id: "all",
    label: "我的文库",
    level: "all",
    count: papers.length,
    target: EMPTY_TARGET,
    children: cloneSeedNodes(),
  };

  for (const child of root.children) {
    child.count = countForNode(papers, child);
    syncChildCounts(papers, child);
  }

  const knownIds = new Set(flattenTree(root).map((node) => node.id));
  const dynamicRoot = buildDynamicClassificationTree(papers);
  for (const node of dynamicRoot.children) {
    if (!knownIds.has(node.id)) {
      root.children.push(node);
    }
  }

  return root;
}

export function flattenTree(node: ClassificationTreeNode): ClassificationTreeNode[] {
  return [node, ...node.children.flatMap((child) => flattenTree(child))];
}

export function matchesTreeNode(paper: PaperRecord, node: ClassificationTreeNode): boolean {
  if (node.level === "all") {
    return true;
  }
  if (node.system === "unclassified") {
    return isUncategorizedPaper(paper);
  }
  if (node.system === "recent") {
    return daysSince(paper.updated_at) <= 14;
  }
  if (node.system === "to_read") {
    return paper.read_status !== "read" || paper.review_status === "pending";
  }

  const source = classificationFromPaper(paper);
  if (node.level === "domain") {
    return source.domain === node.target.domain;
  }
  if (node.level === "area") {
    return source.domain === node.target.domain && source.area === node.target.area;
  }
  return sameClassification(source, node.target);
}

export function classificationNodeId(target: ClassificationTarget): string {
  const domain = treeKey(target.domain || "unclassified");
  if (!target.domain) {
    return `domain:${domain}`;
  }
  if (!target.area && !target.topic) {
    return `domain:${domain}`;
  }
  if (!target.area && target.topic) {
    return `domain:${domain}:topic:${treeKey(target.topic)}`;
  }
  const area = treeKey(target.area);
  if (!target.topic) {
    return `domain:${domain}:area:${area}`;
  }
  return `domain:${domain}:area:${area}:topic:${treeKey(target.topic)}`;
}

export function classificationFromPaper(paper: Pick<PaperRecord, "domain" | "area" | "topic">): ClassificationTarget {
  return {
    domain: cleanClassification(paper.domain),
    area: cleanClassification(paper.area),
    topic: cleanClassification(paper.topic),
  };
}

export function sameClassification(left: ClassificationTarget, right: ClassificationTarget): boolean {
  return cleanClassification(left.domain) === cleanClassification(right.domain) && cleanClassification(left.area) === cleanClassification(right.area) && cleanClassification(left.topic) === cleanClassification(right.topic);
}

export function buildClassificationOptions(papers: PaperRecord[]): ClassificationOptionSet {
  const domains = new Set<string>();
  const areas = new Set<string>();
  const topics = new Set<string>();
  const areasByDomain = new Map<string, Set<string>>();
  const topicsByDomainArea = new Map<string, Set<string>>();

  for (const paper of papers) {
    const domain = cleanClassification(paper.domain);
    const area = cleanClassification(paper.area);
    const topic = cleanClassification(paper.topic);

    if (!domain) continue;
    domains.add(domain);

    if (area) {
      areas.add(area);
      ensureSetEntry(areasByDomain, domain).add(area);
    }

    if (topic) {
      topics.add(topic);
      if (area) {
        ensureSetEntry(topicsByDomainArea, classificationKey(domain, area)).add(topic);
      }
    }
  }

  return {
    domains: sortedValues(domains),
    areas: sortedValues(areas),
    topics: sortedValues(topics),
    areasByDomain: mapToSortedRecord(areasByDomain),
    topicsByDomainArea: mapToSortedRecord(topicsByDomainArea),
  };
}

export function getClassificationChoices(options: ClassificationOptionSet, selection: ClassificationFilterState | ClassificationTarget): {
  domains: string[];
  areas: string[];
  topics: string[];
} {
  const domain = cleanClassification(selection.domain);
  const area = cleanClassification(selection.area);
  const topic = cleanClassification(selection.topic);

  const domains = ensureValue(options.domains, domain);
  const areas = domain ? ensureValue(options.areasByDomain[domain] ?? [], area) : ensureValue(options.areas, area);
  const topics = domain && area
    ? ensureValue(options.topicsByDomainArea[classificationKey(domain, area)] ?? [], topic)
    : domain
      ? ensureValue(collectTopicsForDomain(options, domain), topic)
      : ensureValue(options.topics, topic);

  return { domains, areas, topics };
}

export function comparePapers(left: PaperRecord, right: PaperRecord, sort: SortState | SortKey): number {
  const sortState: SortState = typeof sort === "string" ? { key: sort, direction: "desc" } : sort;
  const direction = sortState.direction === "asc" ? 1 : -1;
  let result = 0;

  if (sortState.key === "title") {
    result = left.title.localeCompare(right.title);
  } else if (sortState.key === "venue") {
    result = (left.venue || "").localeCompare(right.venue || "");
  } else if (sortState.key === "year") {
    result = (left.year ?? 0) - (right.year ?? 0);
  } else if (sortState.key === "tags") {
    result = left.tags.join(",").localeCompare(right.tags.join(","));
  } else if (sortState.key === "status") {
    result = derivePaperStatus(left).localeCompare(derivePaperStatus(right));
  } else {
    result = new Date(left.updated_at).getTime() - new Date(right.updated_at).getTime();
  }

  return (result || left.title.localeCompare(right.title)) * direction;
}

export function tagCounts(papers: PaperRecord[]): Array<[string, number]> {
  return counts(papers.flatMap((paper) => paper.tags));
}

export function derivePaperStatus(paper: PaperRecord): string {
  if (paper.workflow_status) return paper.workflow_status;
  if (isUncategorizedPaper(paper)) return "unclassified";
  if (paper.asset_status === "missing_pdf" || !paper.paper_path) return "missing_pdf";
  if (paper.parser_status === "failed") return "parse-failed";
  if (paper.parser_status === "parsed") return paper.note_path ? "processed" : "parsed";
  if (paper.parser_status === "not_started") return "not_started";
  return paper.review_status || paper.status || "pending";
}

export function paperListItemView(paper: PaperRecord): PaperListItemView {
  return {
    ...paper,
    displayStatus: derivePaperStatus(paper),
    missingFields: missingFieldsForPaper(paper),
  };
}

export function filterPapersByQuery(papers: PaperRecord[], query: string): PaperRecord[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return papers;
  }
  return papers.filter((paper) => {
    const text = `${paper.title} ${paper.venue} ${paper.year ?? ""} ${paper.domain} ${paper.area} ${paper.topic} ${paper.tags.join(" ")} ${paper.path}`.toLowerCase();
    return text.includes(needle);
  });
}

export function filterPapersByClassification(papers: PaperRecord[], filters: ClassificationFilterState): PaperRecord[] {
  const domain = cleanClassification(filters.domain);
  const area = cleanClassification(filters.area);
  const topic = cleanClassification(filters.topic);

  if (!domain && !area && !topic) {
    return papers;
  }

  return papers.filter((paper) => {
    const source = classificationFromPaper(paper);
    return (!domain || source.domain === domain)
      && (!area || source.area === area)
      && (!topic || source.topic === topic);
  });
}

export function candidateScore(candidate: CandidateRecord): number {
  return Math.round((candidate.quality + candidate.relevance) / 2);
}

export function filterCandidates(candidates: CandidateRecord[], filters: {
  batchId?: string;
  minScore: number;
  maxScore: number;
}): CandidateRecord[] {
  return candidates.filter((candidate) => {
    const score = candidateScore(candidate);
    return (!filters.batchId || filters.batchId === "all" || candidate.batch_id === filters.batchId)
      && score >= filters.minScore
      && score <= filters.maxScore;
  });
}

export function libraryOverviewStats(papers: PaperRecord[]): LibraryOverviewStats {
  const now = Date.now();
  const weekMs = 7 * 24 * 60 * 60 * 1000;
  return {
    total: papers.length,
    unclassified: papers.filter(isUncategorizedPaper).length,
    missingPdf: papers.filter((paper) => paper.asset_status === "missing_pdf" || !paper.paper_path).length,
    parsed: papers.filter((paper) => paper.parser_status === "parsed").length,
    parseFailed: papers.filter((paper) => paper.parser_status === "failed").length,
    notes: papers.filter((paper) => Boolean(paper.note_path)).length,
    thisWeek: papers.filter((paper) => now - new Date(paper.updated_at).getTime() <= weekMs).length,
    recentParseSuccess: papers.filter((paper) => paper.parser_status === "parsed" && now - new Date(paper.updated_at).getTime() <= weekMs).length,
  };
}

export function groupQueueByWorkflow(papers: PaperRecord[]): Array<{ label: string; status: string; items: PaperRecord[] }> {
  return [
    { label: "缺少 PDF", status: "missing_pdf", items: papers.filter((paper) => paper.asset_status === "missing_pdf" || !paper.paper_path) },
    { label: "待解析", status: "not_started", items: papers.filter((paper) => paper.paper_path && paper.parser_status === "not_started") },
    { label: "待分类", status: "unclassified", items: papers.filter(isUncategorizedPaper) },
    { label: "待生成 Note", status: "parsed", items: papers.filter((paper) => paper.parser_status === "parsed" && !paper.note_path) },
    { label: "待审阅", status: "pending", items: papers.filter((paper) => paper.review_status === "pending") },
  ];
}

export function domainDistribution(papers: PaperRecord[]): Array<[string, number]> {
  return counts(papers.map((paper) => cleanClassification(paper.domain) || "未分类"));
}

export function localClassifySuggestion(paper: PaperRecord): ClassificationTarget & { tags: string[]; confidence: number } {
  const haystack = `${paper.title} ${paper.venue} ${paper.topic} ${paper.area} ${paper.tags.join(" ")}`.toLowerCase();
  if (haystack.includes("multimodal") || haystack.includes("mllm") || haystack.includes("vision-language")) {
    return { domain: "多模态大模型", area: "Multimodal Learning", topic: "MLLM", tags: ["MLLM", "Multimodal"], confidence: 82 };
  }
  if (haystack.includes("action") || haystack.includes("prediction")) {
    return { domain: "Action Prediction", area: "Behavior Modeling", topic: "Action Prediction", tags: ["Action Prediction"], confidence: 78 };
  }
  if (haystack.includes("augmentation")) {
    return { domain: "Data Augmentation", area: "Training Data", topic: "Augmentation", tags: ["Data Augmentation"], confidence: 74 };
  }
  if (haystack.includes("environment")) {
    return { domain: "Environment Understanding", area: "Scene Understanding", topic: "Environment Understanding", tags: ["Environment"], confidence: 72 };
  }
  return { domain: "Representation Learning", area: "General", topic: "Representation Learning", tags: ["Representation"], confidence: 64 };
}

function buildDynamicClassificationTree(papers: PaperRecord[]): ClassificationTreeNode {
  const root: ClassificationTreeNode = {
    id: "dynamic",
    label: "dynamic",
    level: "all",
    count: papers.length,
    target: EMPTY_TARGET,
    children: [],
  };
  const domains = new Map<string, ClassificationTreeNode>();

  for (const paper of papers) {
    const target = classificationFromPaper(paper);
    if (!target.domain) {
      continue;
    }
    const domainKey = treeKey(target.domain);
    let domainNode = domains.get(domainKey);
    if (!domainNode) {
      domainNode = {
        id: classificationNodeId({ domain: target.domain, area: "", topic: "" }),
        label: target.domain,
        level: "domain",
        count: 0,
        target: { domain: target.domain, area: "", topic: "" },
        children: [],
      };
      domains.set(domainKey, domainNode);
      root.children.push(domainNode);
    }
    domainNode.count += 1;

    if (!target.area && !target.topic) {
      continue;
    }

    const areaId = target.area ? classificationNodeId({ domain: target.domain, area: target.area, topic: "" }) : `domain:${treeKey(target.domain)}:area:unassigned`;
    let areaNode = domainNode.children.find((node) => node.id === areaId);
    if (!areaNode) {
      areaNode = {
        id: areaId,
        label: target.area || "未指定 Area",
        level: "area",
        count: 0,
        target: { domain: target.domain, area: target.area, topic: "" },
        children: [],
      };
      domainNode.children.push(areaNode);
    }
    areaNode.count += 1;

    if (!target.topic) {
      continue;
    }

    let topicNode = areaNode.children.find((node) => node.id === classificationNodeId(target));
    if (!topicNode) {
      topicNode = {
        id: classificationNodeId(target),
        label: target.topic,
        level: "topic",
        count: 0,
        target,
        children: [],
      };
      areaNode.children.push(topicNode);
    }
    topicNode.count += 1;
  }

  sortTree(root);
  return root;
}

function systemNode(system: "recent" | "to_read" | "unclassified", label: string): ClassificationTreeNode {
  return {
    id: `system:${system}`,
    label,
    level: "system",
    count: 0,
    target: EMPTY_TARGET,
    children: [],
    system,
  };
}

function domainSeed(domain: string): ClassificationTreeNode {
  return {
    id: classificationNodeId({ domain, area: "", topic: "" }),
    label: domain,
    level: "domain",
    count: 0,
    target: { domain, area: "", topic: "" },
    children: [],
  };
}

function topicSeed(domain: string, topic: string): ClassificationTreeNode {
  return {
    id: classificationNodeId({ domain, area: "", topic }),
    label: topic,
    level: "topic",
    count: 0,
    target: { domain, area: "", topic },
    children: [],
  };
}

function cloneSeedNodes(): ClassificationTreeNode[] {
  return DOMAIN_TREE_SEEDS.map((node) => ({
    ...node,
    target: { ...node.target },
    children: node.children.map((child) => ({ ...child, target: { ...child.target }, children: [] })),
  }));
}

function countForNode(papers: PaperRecord[], node: ClassificationTreeNode): number {
  return papers.filter((paper) => matchesTreeNode(paper, node)).length;
}

function syncChildCounts(papers: PaperRecord[], node: ClassificationTreeNode): void {
  for (const child of node.children) {
    child.count = countForNode(papers, child);
    syncChildCounts(papers, child);
  }
}

function cleanClassification(value: string): string {
  const normalized = value.trim();
  return normalized === "unclassified" || normalized === "all" ? "" : normalized;
}

function sortTree(node: ClassificationTreeNode): void {
  node.children.sort((left, right) => left.label.localeCompare(right.label));
  for (const child of node.children) {
    sortTree(child);
  }
}

function treeKey(value: string): string {
  return value.trim().toLowerCase();
}

function counts(values: string[]): Array<[string, number]> {
  const map = new Map<string, number>();
  for (const value of values) {
    if (!value) {
      continue;
    }
    map.set(value, (map.get(value) ?? 0) + 1);
  }
  return Array.from(map.entries()).sort((left, right) => right[1] - left[1]);
}

function ensureSetEntry(map: Map<string, Set<string>>, key: string): Set<string> {
  const existing = map.get(key);
  if (existing) {
    return existing;
  }
  const next = new Set<string>();
  map.set(key, next);
  return next;
}

function classificationKey(domain: string, area: string): string {
  return `${domain}\u0000${area}`;
}

function sortedValues(values: Set<string>): string[] {
  return Array.from(values).sort((left, right) => left.localeCompare(right));
}

function mapToSortedRecord(map: Map<string, Set<string>>): Record<string, string[]> {
  return Object.fromEntries(Array.from(map.entries()).map(([key, values]) => [key, sortedValues(values)]));
}

function ensureValue(values: string[], value: string): string[] {
  if (!value || values.includes(value)) {
    return values;
  }
  return [...values, value].sort((left, right) => left.localeCompare(right));
}

function collectTopicsForDomain(options: ClassificationOptionSet, domain: string): string[] {
  const topics = new Set<string>();
  const prefix = `${domain}\u0000`;
  for (const [key, values] of Object.entries(options.topicsByDomainArea)) {
    if (!key.startsWith(prefix)) {
      continue;
    }
    for (const value of values) {
      topics.add(value);
    }
  }
  return sortedValues(topics);
}

function daysSince(value: string): number {
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) {
    return Number.POSITIVE_INFINITY;
  }
  return (Date.now() - time) / (24 * 60 * 60 * 1000);
}
