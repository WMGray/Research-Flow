import { request } from "@/lib/http";

export type CategoryRecord = {
  category_id: number;
  name: string;
  parent_id: number | null;
  path: string;
  sort_order: number;
  paper_count: number;
  children?: CategoryRecord[];
};

export async function listCategories(): Promise<CategoryRecord[]> {
  const envelope = await request<CategoryRecord[]>("/api/v1/categories");
  return envelope.data;
}

export async function createCategory(input: {
  name: string;
  parent_id?: number | null;
  sort_order?: number;
}): Promise<CategoryRecord> {
  const envelope = await request<CategoryRecord>("/api/v1/categories", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function deleteCategory(categoryId: number): Promise<void> {
  await request<unknown>(`/api/v1/categories/${categoryId}`, {
    method: "DELETE",
  });
}
