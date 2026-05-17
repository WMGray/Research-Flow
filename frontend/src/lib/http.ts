export async function getJson<T>(url: string): Promise<T> {
  const response = await safeFetch(url, {
    headers: {
      Accept: "application/json"
    }
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function postJson<T>(url: string, body: unknown = {}): Promise<T> {
  const response = await safeFetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function patchJson<T>(url: string, body: unknown = {}): Promise<T> {
  const response = await safeFetch(url, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error: unknown) {
    throw new Error(buildNetworkErrorMessage(error));
  }
}

function buildNetworkErrorMessage(error: unknown): string {
  const fallback = "无法连接后端 API。请确认前端与后端已启动，或检查 VITE_API_BASE_URL / /api 代理配置。";
  if (!(error instanceof Error)) {
    return fallback;
  }
  if (error.message === "Failed to fetch") {
    return fallback;
  }
  return `${fallback} 原始错误: ${error.message}`;
}
