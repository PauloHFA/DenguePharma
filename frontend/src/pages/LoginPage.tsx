import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { session, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <h1>DenguePharma</h1>
      <p className="muted">Plataforma de curadoria rastreável de evidências sobre intervenções farmacológicas para dengue.</p>
      <form onSubmit={onSubmit} aria-labelledby="login-title">
        <h2 id="login-title">Entrar</h2>
        <label htmlFor="email">E-mail</label>
        <input id="email" type="email" autoComplete="username" required value={email}
               onChange={(e) => setEmail(e.target.value)} />
        <label htmlFor="password">Senha</label>
        <input id="password" type="password" autoComplete="current-password" required value={password}
               onChange={(e) => setPassword(e.target.value)} />
        {error && <p role="alert" className="error">Erro: {error}</p>}
        <button type="submit" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
      </form>
      <p className="notice">
        Uso restrito a pesquisa e consulta de evidências. Esta plataforma não realiza diagnóstico, prescrição nem
        recomendação de dose.
      </p>
    </main>
  );
}

