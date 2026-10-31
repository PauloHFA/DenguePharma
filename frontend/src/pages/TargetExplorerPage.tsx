import { useState } from "react";
import { Molecule3DViewer } from "../components/Molecule3DViewer";

interface Target {
  id: string;
  name: string;
  category: "NAO_ESTRUTURAL" | "ESTRUTURAL" | "HOSPEDEIRO";
  role: string;
  domains: string;
  serotypes: string[];
  inhibitors: Array<{ name: string; mechanism: string; stage: string; pubchemCid?: string }>;
  pdbIds: string[];
  description: string;
}

const TARGETS: Target[] = [
  {
    id: "NS5",
    name: "NS5 (Polimerase RdRp & Metiltransferase)",
    category: "NAO_ESTRUTURAL",
    role: "Replicação do genoma de RNA e capeamento na extremidade 5' (proteção contra imunidade inata)",
    domains: "N-terminal: Metiltransferase (MTase) | C-terminal: RNA polimerase dependente de RNA (RdRp)",
    serotypes: ["DENV-1", "DENV-2", "DENV-3", "DENV-4"],
    inhibitors: [
      { name: "Balapiravir (R1626)", mechanism: "Pró-fármaco análogo de nucleosídeo inibidor da RdRp", stage: "Ensaio Clínico Fase 2", pubchemCid: "11561674" },
      { name: "Sofosbuvir", mechanism: "Inibidor análogo de uridina da RdRp (reposicionamento de HCV)", stage: "Estudo Clínico / In vitro", pubchemCid: "45375808" },
      { name: "NITD-008", mechanism: "Análogo de adenosina bloqueador de elongação da RdRp", stage: "Pré-clínico", pubchemCid: "44468277" },
      { name: "Sinefungina", mechanism: "Análogo de SAM inibidor competitivo da MTase", stage: "Pré-clínico (pesquisa básica)", pubchemCid: "54682496" },
    ],
    pdbIds: ["5ZQK", "4V0R", "2J7U", "4V0Q"],
    description: "A proteína NS5 é a maior e mais conservada enzima do vírus da dengue (~103 kDa). Apresenta alta identidade estrutural entre os 4 sorotipos, sendo o alvo principal para antivirais pan-sorotipo de ação direta.",
  },
  {
    id: "NS3",
    name: "NS3 (Serino Protease & RNA Helicase)",
    category: "NAO_ESTRUTURAL",
    role: "Processamento proteolítico da poliproteína viral (com cofator NS2B) e desenrolamento do dsRNA",
    domains: "N-terminal: Serino protease (tríade catalítica His51-Asp75-Ser135) | C-terminal: RNA helicase / NTPase",
    serotypes: ["DENV-1", "DENV-2", "DENV-3", "DENV-4"],
    inhibitors: [
      { name: "Ivermectina", mechanism: "Inibidor alostérico da atividade de helicase / importação nuclear", stage: "Ensaio Clínico Fase 2/3 (inconclusivo)", pubchemCid: "6321424" },
      { name: "Suramina", mechanism: "Inibidor competitivo de helicase e ligação de nucleotídeo", stage: "Pré-clínico", pubchemCid: "5361" },
      { name: "Peptidomiméticos NS2B-NS3", mechanism: "Inibição do sítio ativo da protease serina", stage: "Desenvolvimento pré-clínico", pubchemCid: "54682500" },
    ],
    pdbIds: ["2FOM", "2BHR", "2VBC", "6MO1"],
    description: "A protease NS3 forma um complexo heterodimérico essencial com o cofator de membrana NS2B para clivar a poliproteína precursora nas junções NS2A/NS2B, NS2B/NS3, NS3/NS4A e NS4B/NS5.",
  },
  {
    id: "PROTEINA_E",
    name: "Proteína de Envelope (E)",
    category: "ESTRUTURAL",
    role: "Ligação ao receptor celular do hospedeiro e fusão da membrana viral dependente de pH baixo",
    domains: "Domínio I (central), Domínio II (alça de fusão hidrofóbica), Domínio III (ligação ao receptor)",
    serotypes: ["DENV-1", "DENV-2", "DENV-3", "DENV-4"],
    inhibitors: [
      { name: "Cloroquina / Hidroxicloroquina", mechanism: "Inibição de fusão por alcalinização de endossomos", stage: "Ensaio Clínico (sem benefício sustentado)", pubchemCid: "2719" },
      { name: "JNJ-1802 / JNJ-A07", mechanism: "Bloqueador da interação NS3-NS4B e modulação conformacional de E", stage: "Ensaio Clínico Fase 1/2", pubchemCid: "163080645" },
    ],
    pdbIds: ["1OAN", "1TG8", "3J27", "4UT6"],
    description: "Principal antígeno da superfície do vírion de dengue. Forma 90 homodímeros que sofrem transição conformacional irreversível para trímeros no ambiente ácido do endossomo tardio.",
  },
  {
    id: "HOST_TARGETS",
    name: "Alvos Celulares do Hospedeiro (Host Factors)",
    category: "HOSPEDEIRO",
    role: "Dependência de maquinário celular para entrada, replicação e evasão da resposta imune",
    domains: "Importinas nucleares (KPNA/KPNB1) | Glicosidases do RE | Biossíntese de pirimidinas (DHODH)",
    serotypes: ["Pan-sorotipo (DENV 1-4)"],
    inhibitors: [
      { name: "Celgosivir (MX-3253)", mechanism: "Inibidor de alfa-glicosidase I do retículo endoplasmático", stage: "Ensaio Clínico Fase 1b/2", pubchemCid: "9576787" },
      { name: "Brequinar", mechanism: "Inibidor potente de di-hidroorotato desidrogenase (DHODH)", stage: "Pré-clínico avançado", pubchemCid: "5702160" },
      { name: "Lovastatina", mechanism: "Inibidor de HMG-CoA redutase (vias de biogênese lipídica)", stage: "Ensaio Clínico Fase 2 (sem efeito antiviral)", pubchemCid: "53232" },
    ],
    pdbIds: ["3TJ3", "1D3G", "4YLW"],
    description: "Fármacos direcionados a alvos do hospedeiro apresentam menor propensão a induzir resistência viral por mutação rápida, mas exigem rigorosa caracterização da janela terapêutica e toxicidade.",
  },
];

export function TargetExplorerPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedTarget, setSelectedTarget] = useState<Target>(TARGETS[0]);

  const filteredTargets = selectedCategory
    ? TARGETS.filter((t) => t.category === selectedCategory)
    : TARGETS;

  return (
    <section aria-labelledby="target-heading">
      <h1 id="target-heading">Explorador de Alvos Biológicos Moleculares (Target Explorer)</h1>
      <p>
        Mapeamento de alvos virais do Flavivírus da Dengue (DENV 1-4) e fatores do hospedeiro.
        Consulte funções enzimáticas, domínios estruturais, estruturas tridimensionais no PDB e inibidores candidatos documentados.
      </p>

      <div className="filter-bar">
        <label>
          Categoria de Alvo:{" "}
          <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}>
            <option value="">Todos os alvos</option>
            <option value="NAO_ESTRUTURAL">Proteínas Não Estruturais (NS5, NS3)</option>
            <option value="ESTRUTURAL">Proteínas Estruturais (E, prM, C)</option>
            <option value="HOSPEDEIRO">Fatores do Hospedeiro (Host Targets)</option>
          </select>
        </label>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.5rem", marginTop: "1rem" }}>
        <aside style={{ borderRight: "1px solid #e5e7eb", paddingRight: "1rem" }}>
          <h3>Alvos Mapeados</h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {filteredTargets.map((t) => (
              <li key={t.id} style={{ marginBottom: "0.5rem" }}>
                <button
                  type="button"
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "0.6rem 0.8rem",
                    borderRadius: "6px",
                    border: "1px solid",
                    borderColor: selectedTarget.id === t.id ? "#2563eb" : "#e5e7eb",
                    background: selectedTarget.id === t.id ? "#eff6ff" : "#fff",
                    fontWeight: selectedTarget.id === t.id ? "bold" : "normal",
                    cursor: "pointer",
                  }}
                  onClick={() => setSelectedTarget(t)}
                >
                  {t.name}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <article className="card" style={{ padding: "1.5rem" }}>
          <h2>{selectedTarget.name}</h2>
          <p style={{ fontSize: "1.05rem" }}>{selectedTarget.description}</p>

          <table style={{ margin: "1rem 0" }}>
            <tbody>
              <tr>
                <td style={{ width: "200px" }}><strong>Papel Biológico:</strong></td>
                <td>{selectedTarget.role}</td>
              </tr>
              <tr>
                <td><strong>Domínios Catalíticos:</strong></td>
                <td>{selectedTarget.domains}</td>
              </tr>
              <tr>
                <td><strong>Sorotipos Afetados:</strong></td>
                <td>
                  {selectedTarget.serotypes.map((s) => (
                    <span key={s} style={{ display: "inline-block", background: "#e0f2fe", color: "#0369a1", padding: "0.15rem 0.5rem", borderRadius: "4px", marginRight: "0.4rem", fontSize: "0.85rem" }}>
                      {s}
                    </span>
                  ))}
                </td>
              </tr>
              <tr>
                <td><strong>Códigos PDB de Referência:</strong></td>
                <td>
                  {selectedTarget.pdbIds.map((pdb) => (
                    <a
                      key={pdb}
                      href={`https://www.rcsb.org/structure/${pdb}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ marginRight: "0.8rem", textDecoration: "underline" }}
                    >
                      PDB {pdb} ↗
                    </a>
                  ))}
                </td>
              </tr>
            </tbody>
          </table>

          <h3>Fármacos e Inibidores Candidatos Documentados</h3>
          {selectedTarget.inhibitors.find((i) => i.pubchemCid) && (
            <div style={{ marginBottom: "1.2rem" }}>
              <Molecule3DViewer
                cid={selectedTarget.inhibitors.find((i) => i.pubchemCid)?.pubchemCid}
                name={selectedTarget.inhibitors.find((i) => i.pubchemCid)?.name || ""}
                height={260}
              />
            </div>
          )}
          <table>
            <thead>
              <tr>
                <th>Composto</th>
                <th>Mecanismo Proposto</th>
                <th>Estágio / Contexto</th>
                <th>Estrutura PubChem</th>
              </tr>
            </thead>
            <tbody>
              {selectedTarget.inhibitors.map((inh) => (
                <tr key={inh.name}>
                  <td><strong>{inh.name}</strong></td>
                  <td>{inh.mechanism}</td>
                  <td><code>{inh.stage}</code></td>
                  <td>
                    {inh.pubchemCid ? (
                      <a
                        href={`https://pubchem.ncbi.nlm.nih.gov/compound/${inh.pubchemCid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        CID {inh.pubchemCid} ↗
                      </a>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <p className="notice" style={{ marginTop: "1.5rem" }}>
            Nota Metodológica: A inibição in vitro de enzimas recombinantes não garante biodisponibilidade intracelular ou benefício clínico em pacientes (Regra RC-01).
          </p>
        </article>
      </div>
    </section>
  );
}

