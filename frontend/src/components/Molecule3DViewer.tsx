import { useState } from "react";

interface Molecule3DProps {
  cid?: string | number;
  name: string;
  width?: number | string;
  height?: number | string;
}

/**
 * Componente de visualização química 3D interativa utilizando embedding do PubChem 3D viewer.
 * Permite rotação, zoom e inspeção conformacional sem dependências pesadas de bundle.
 */
export function Molecule3DViewer({ cid, name, width = "100%", height = 300 }: Molecule3DProps) {
  const [mode, setMode] = useState<"3D" | "2D">("3D");

  if (!cid) {
    return (
      <div
        style={{
          width,
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f8fafc",
          border: "1px dashed #cbd5e1",
          borderRadius: 6,
          color: "#64748b",
          fontSize: "0.85rem",
        }}
      >
        Estrutura 3D indisponível (CID não mapeado para {name})
      </div>
    );
  }

  const embedUrl3d = `https://pubchem.ncbi.nlm.nih.gov/compound/${cid}#section=3D-Conformer&embed=true`;
  const imgUrl2d = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?image_size=300x300`;

  return (
    <div style={{ width, border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden", backgroundColor: "#fff" }}>
      <div
        style={{
          padding: "6px 12px",
          backgroundColor: "#f1f5f9",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#1e293b" }}>
          Estrutura Molecular: {name} (PubChem CID: {cid})
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          <button
            type="button"
            onClick={() => setMode("3D")}
            style={{
              padding: "2px 8px",
              fontSize: "0.75rem",
              borderRadius: 4,
              border: "1px solid #cbd5e1",
              backgroundColor: mode === "3D" ? "#0284c7" : "#fff",
              color: mode === "3D" ? "#fff" : "#334155",
              cursor: "pointer",
            }}
          >
            Conformação 3D
          </button>
          <button
            type="button"
            onClick={() => setMode("2D")}
            style={{
              padding: "2px 8px",
              fontSize: "0.75rem",
              borderRadius: 4,
              border: "1px solid #cbd5e1",
              backgroundColor: mode === "2D" ? "#0284c7" : "#fff",
              color: mode === "2D" ? "#fff" : "#334155",
              cursor: "pointer",
            }}
          >
            Diagrama 2D
          </button>
        </div>
      </div>

      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
        {mode === "3D" ? (
          <iframe
            title={`Estrutura 3D de ${name}`}
            src={embedUrl3d}
            style={{ width: "100%", height: "100%", border: "none" }}
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <img
            src={imgUrl2d}
            alt={`Estrutura 2D de ${name}`}
            style={{ maxHeight: "90%", maxWidth: "90%", objectFit: "contain" }}
          />
        )}
      </div>
      <div style={{ padding: "4px 8px", fontSize: "0.7rem", color: "#64748b", backgroundColor: "#f8fafc", textAlign: "right" }}>
        Fonte: PubChem PUG REST / NCBI Conformers. Uso restrito a pesquisa (RC-01).
      </div>
    </div>
  );
}
