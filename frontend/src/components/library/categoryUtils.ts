import type { CategoryRecord } from "@/lib/api";

export type FlatCategory = CategoryRecord & {
  depth: number;
  label: string;
};

export function flattenCategories(
  categories: CategoryRecord[],
  depth = 0,
): FlatCategory[] {
  return categories.flatMap((category) => [
    {
      ...category,
      depth,
      label: `${"  ".repeat(depth)}${depth > 0 ? "- " : ""}${category.name}`,
    },
    ...flattenCategories(category.children ?? [], depth + 1),
  ]);
}
