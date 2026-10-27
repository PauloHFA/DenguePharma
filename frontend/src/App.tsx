import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { hasAnyRole } from "./auth/roles";
import { LoginPage } from "./pages/LoginPage";
import { ImportsPage } from "./pages/ImportsPage";
import { ProtocolsPage } from "./pages/ProtocolsPage";
import { ScreenPage } from "./pages/ScreenPage";
import { SCREENS } from "./screens";

function Shell() {
  const { session, logout } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  const visible = SCREENS.filter((s) => hasAnyRole(session, s.roles));

  return (
    <div className="shell">
      <header>
        <strong>DenguePharma</strong>
        <span className="muted">
          {session.email} ({session.roles.join(", ")})
        </span>
        <button type="button" onClick={logout}>Sair</button>
      </header>
      <nav aria-label="Principal">
        <ul>
          {visible.map((s) => (
            <li key={s.path}>
              <NavLink to={`/${s.path}`}>{s.title}</NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <Outlet />
      </main>
      <footer className="notice">
        Pesquisa e consulta de evidências. Sem diagnóstico, prescrição ou recomendação de dose.
      </footer>
    </div>
  );
}

function Home() {
  const { session } = useAuth();
  const first = SCREENS.find((s) => hasAnyRole(session, s.roles));
  return first ? <Navigate to={`/${first.path}`} replace /> : <p>Sem telas disponíveis para o seu perfil.</p>;
}

function Guarded({ path }: { path: string }) {
  const { session } = useAuth();
  const screen = SCREENS.find((s) => s.path === path)!;
  if (!hasAnyRole(session, screen.roles)) {
    return <p role="alert">Acesso limitado: seu perfil não tem permissão para esta tela.</p>;
  }
  if (path === "protocolos") return <ProtocolsPage />;
  if (path === "importacoes") return <ImportsPage />;
  return <ScreenPage screen={screen} />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Shell />}>
        <Route index element={<Home />} />
        {SCREENS.map((s) => (
          <Route key={s.path} path={s.path} element={<Guarded path={s.path} />} />
        ))}
        <Route path="*" element={<p>Página não encontrada.</p>} />
      </Route>
    </Routes>
  );
}

