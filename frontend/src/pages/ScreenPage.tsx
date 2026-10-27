import type { ScreenDef } from "../screens";

export function ScreenPage({ screen }: { screen: ScreenDef }) {
  return (
    <section aria-labelledby="screen-title">
      <h1 id="screen-title">{screen.title}</h1>
      <p>{screen.description}</p>
      <div className="empty" role="status">
        <strong>Estado vazio:</strong> {screen.emptyMessage}
      </div>
    </section>
  );
}

