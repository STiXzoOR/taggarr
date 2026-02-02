const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message?: string
  ) {
    super(message || statusText);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, response.statusText, text);
  }
  return response.json();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      credentials: "include",
    }).then(handleResponse),

  logout: () =>
    fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      credentials: "include",
    }).then(handleResponse),

  getAuthStatus: () =>
    fetch(`${API_BASE}/auth/status`, {
      credentials: "include",
    }).then(
      handleResponse<{
        authenticated: boolean;
        user: { username: string } | null;
        initialized: boolean;
      }>
    ),

  initialize: (username: string, password: string) =>
    fetch(`${API_BASE}/initialize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      credentials: "include",
    }).then(handleResponse),

  // Stats
  getStats: () =>
    fetch(`${API_BASE}/stats`, { credentials: "include" }).then(handleResponse),

  getSystemStatus: () =>
    fetch(`${API_BASE}/system/status`, { credentials: "include" }).then(
      handleResponse
    ),

  // Instances
  getInstances: () =>
    fetch(`${API_BASE}/instance`, { credentials: "include" }).then(
      handleResponse
    ),

  getInstance: (id: number) =>
    fetch(`${API_BASE}/instance/${id}`, { credentials: "include" }).then(
      handleResponse
    ),

  createInstance: (data: unknown) =>
    fetch(`${API_BASE}/instance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      credentials: "include",
    }).then(handleResponse),

  updateInstance: (id: number, data: unknown) =>
    fetch(`${API_BASE}/instance/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      credentials: "include",
    }).then(handleResponse),

  deleteInstance: (id: number) =>
    fetch(`${API_BASE}/instance/${id}`, {
      method: "DELETE",
      credentials: "include",
    }),

  // Media
  getMedia: (params?: {
    page?: number;
    page_size?: number;
    instance_id?: number;
    tag_id?: number;
    search?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    return fetch(`${API_BASE}/media?${searchParams}`, {
      credentials: "include",
    }).then(handleResponse);
  },

  // Tags
  getTags: () =>
    fetch(`${API_BASE}/tag`, { credentials: "include" }).then(handleResponse),

  // Config
  getConfig: (key: string) =>
    fetch(`${API_BASE}/config/${key}`, { credentials: "include" }).then(
      handleResponse
    ),

  setConfig: (key: string, value: string) =>
    fetch(`${API_BASE}/config/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
      credentials: "include",
    }).then(handleResponse),

  getUIConfig: () =>
    fetch(`${API_BASE}/config/ui`, { credentials: "include" }).then(
      handleResponse
    ),
};
