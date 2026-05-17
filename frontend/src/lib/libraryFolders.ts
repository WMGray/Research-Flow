import type { PaperRecord } from "@/lib/api";

export type LibraryFolderTreeNode = {
  id: string;
  label: string;
  count: number;
  path: string;
  kind: "all" | "folder";
  children: LibraryFolderTreeNode[];
};

export type PaneLayoutState = {
  treeWidth: number;
  detailWidth: number;
};

export function buildLibraryFolderTree(papers: PaperRecord[], libraryRoot = "", extraFolderPaths: string[] = []): LibraryFolderTreeNode {
  const root: LibraryFolderTreeNode = {
    id: "all",
    label: rootLabel(libraryRoot),
    count: papers.length,
    path: "",
    kind: "all",
    children: [],
  };

  for (const paper of papers) {
    const folderPath = relativeLibraryFolderPath(paper, libraryRoot);
    if (folderPath) {
      addFolderPath(root, folderPath, 1);
    }
  }

  for (const folderPath of extraFolderPaths) {
    addFolderPath(root, folderPath, 0);
  }

  sortFolderTree(root);
  return root;
}

export function matchesLibraryFolderNode(paper: PaperRecord, node: LibraryFolderTreeNode, libraryRoot = ""): boolean {
  if (node.kind === "all") {
    return true;
  }
  const folderPath = relativeLibraryFolderPath(paper, libraryRoot);
  return folderPath === node.path;
}

export function relativeLibraryFolderPath(paper: Pick<PaperRecord, "path">, libraryRoot = ""): string {
  const relativeParts = relativePaperParts(paper.path, libraryRoot);
  if (relativeParts.length <= 1) {
    return "";
  }
  return relativeParts.slice(0, -1).join("/");
}

function addFolderPath(root: LibraryFolderTreeNode, path: string, countDelta: number): void {
  const parts = path.split("/").filter(Boolean);
  let current = root;
  let currentPath = "";

  for (const part of parts) {
    currentPath = currentPath ? `${currentPath}/${part}` : part;
    let child = current.children.find((node) => node.path === currentPath);
    if (!child) {
      child = {
        id: `folder:${currentPath}`,
        label: part,
        count: 0,
        path: currentPath,
        kind: "folder",
        children: [],
      };
      current.children.push(child);
    }
    child.count += countDelta;
    current = child;
  }
}

function relativePaperParts(path: string, libraryRoot: string): string[] {
  const normalizedPath = normalizePath(path);
  const normalizedRoot = normalizePath(libraryRoot);
  if (!normalizedPath) {
    return [];
  }

  if (normalizedRoot && normalizedPath.toLowerCase().startsWith(normalizedRoot.toLowerCase())) {
    return trimSlashes(normalizedPath.slice(normalizedRoot.length)).split("/").filter(Boolean);
  }

  const parts = normalizedPath.split("/").filter(Boolean);
  const rootName = normalizedRoot.split("/").filter(Boolean).pop();
  if (rootName) {
    const index = parts.findIndex((part) => samePathPart(part, rootName));
    if (index >= 0) {
      return parts.slice(index + 1);
    }
  }

  const folderRootIndex = parts.findIndex((part) => ["01_papers", "papers", "03_papers", "library"].includes(part.toLowerCase()));
  if (folderRootIndex >= 0) {
    return parts.slice(folderRootIndex + 1);
  }

  return parts;
}

function rootLabel(libraryRoot: string): string {
  const parts = normalizePath(libraryRoot).split("/").filter(Boolean);
  return parts[parts.length - 1] || "01_Papers";
}

function sortFolderTree(node: LibraryFolderTreeNode): void {
  node.children.sort((left, right) => left.label.localeCompare(right.label));
  for (const child of node.children) {
    sortFolderTree(child);
  }
}

function samePathPart(left: string, right: string): boolean {
  return left.toLowerCase() === right.toLowerCase();
}

function normalizePath(path: string): string {
  return trimSlashes(path.replace(/\\/g, "/"));
}

function trimSlashes(value: string): string {
  return value.replace(/^\/+|\/+$/g, "");
}
