import type { Session } from "./auth/roles";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(session: Session, path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = ((await res.json()) as { message?: string; detail?: string }).message ?? "";
    } catch {
      /* corpo vazio */
    }
    throw new ApiError(res.status, detail || `Erro ${res.status}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

