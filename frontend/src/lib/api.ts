export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const user = typeof window === "undefined"
    ? "alex@meridianlabs.example"
    : localStorage.getItem("proofgate-demo-user") ?? "alex@meridianlabs.example";
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers: Record<string, string> = {
    "X-Demo-User": user,
    "X-Organization": "meridian-labs",
  };
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...init.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed." }));
    throw new ApiError(response.status, body.detail ?? "Request failed.");
  }
  return response.json() as Promise<T>;
}
