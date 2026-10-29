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
      const error = (await res.json()) as { message?: string; detail?: string };
      detail = error.detail ?? error.message ?? "";
    } catch {
      /* corpo vazio */
    }
    throw new ApiError(res.status, detail || `Erro ${res.status}`);
  }
  const body = await res.text();
  return (body ? JSON.parse(body) : undefined) as T;
}

export async function downloadFile(session: Session, path: string, filename: string): Promise<void> {
  const blob = await readFile(session, path);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

export async function readFile(session: Session, path: string): Promise<Blob> {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${session.token}` } });
  if (!res.ok) throw new ApiError(res.status, `Não foi possível baixar o arquivo (erro ${res.status}).`);
  return res.blob();
}

