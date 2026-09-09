import type {
  AuditPage,
  ChatRequest,
  ChatResponse,
  Metrics,
  PendingAction,
  UserPreferences,
} from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  chat: (req: ChatRequest) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(req) }),

  tasks: {
    list: (params?: { status?: string; owner?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return request(`/api/tasks${qs ? `?${qs}` : ""}`);
    },
    complete: (id: string) => request(`/api/tasks/${id}/complete`, { method: "POST" }),
  },

  email: {
    threads: () => request("/api/email/threads"),
    approveDraft: (threadId: string) =>
      request(`/api/email/draft/${threadId}/approve`, { method: "POST" }),
    rejectDraft: (threadId: string) =>
      request(`/api/email/draft/${threadId}/reject`, { method: "POST" }),
  },

  brief: {
    get: () => request("/api/brief"),
  },

  actions: {
    execute: (action: PendingAction) =>
      request<{ status: string; message: string }>("/api/actions/execute", {
        method: "POST",
        body: JSON.stringify(action),
      }),
    reject: (action: PendingAction) =>
      request<{ status: string; message: string }>("/api/actions/reject", {
        method: "POST",
        body: JSON.stringify(action),
      }),
  },

  preferences: {
    get: () => request<UserPreferences>("/api/preferences"),
    update: (patch: Partial<UserPreferences>) =>
      request<UserPreferences>("/api/preferences", {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
  },

  admin: {
    audit: (params?: {
      module?: string;
      intent?: string;
      has_error?: boolean;
      limit?: number;
      offset?: number;
    }) => {
      const qs = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params ?? {})
            .filter(([, v]) => v !== undefined)
            .map(([k, v]) => [k, String(v)])
        )
      ).toString();
      return request<AuditPage>(`/api/admin/audit${qs ? `?${qs}` : ""}`);
    },
    metrics: () => request<Metrics>("/api/admin/metrics"),
  },
};
