export type Role = "LEITOR" | "REVISOR" | "ADJUDICADOR" | "PESQUISADOR" | "ADMINISTRADOR";

export interface Session {
  token: string;
  email: string;
  roles: Role[];
}

export function hasAnyRole(session: Session | null, allowed: readonly Role[]): boolean {
  if (!session) return false;
  if (allowed.length === 0) return true;
  return session.roles.some((r) => allowed.includes(r));
}

