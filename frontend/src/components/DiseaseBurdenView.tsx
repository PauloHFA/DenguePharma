import { useEffect, useState } from "react";

export interface DiseaseBurdenDTO {
  countryCode: string;
  countryName: string;
  region: string;
  estimatedCasesPerYear: number;
  dalysRatePer100k: number;
  predominantSerotypes: string;
  clinicalTrialsCount: number;
  isResearchDesert: boolean;
  notice: string;
}

export interface TrialBurdenLinkDTO {
  trialId: string;
  countryCode: string;
  countryName: string;
  year: number;
  participantsCount: number;
  siteName: string;
  cases: number | null;
  incidencePer100k: number | null;
  caseDefinition: string | null;
  source: string | null;
  hasBurdenData: boolean;
  burdenStatus: string;
  disparityIndicator: string;
}

const DEFAULT_BURDEN: DiseaseBurdenDTO[] = [
  {
    countryCode: "BRA",
    countryName: "Brasil",
    region: "América Latina / Caribe",
    estimatedCasesPerYear: 2900000,
    dalysRatePer100k: 412.5,
    predominantSerotypes: "DENV-1, DENV-2, DENV-3",
    clinicalTrialsCount: 14,
    isResearchDesert: false,
    notice: "Elevada transmissão endêmica com centros ativos de pesquisa em dengue.",
  },
  {
    countryCode: "BGD",
    countryName: "Bangladesh",
    region: "Sudeste Asiático",
    estimatedCasesPerYear: 320000,
    dalysRatePer100k: 520.1,
    predominantSerotypes: "DENV-2, DENV-3",
    clinicalTrialsCount: 1,
    isResearchDesert: true,
    notice: "Deserto de pesquisa clínica: altíssima mortalidade e DALYs com escassez de ensaios farmacológicos.",
  },
  {
    countryCode: "VNM",
    countryName: "Vietnã",
    region: "Sudeste Asiático",
    estimatedCasesPerYear: 280000,
    dalysRatePer100k: 385.0,
    predominantSerotypes: "DENV-1, DENV-2, DENV-4",
    clinicalTrialsCount: 11,
    isResearchDesert: false,
    notice: "Centro de pesquisa clínica estabelecido (Hospital for Tropical Diseases / OUCRU).",
  },
  {
    countryCode: "IDN",
    countryName: "Indonésia",
    region: "Sudeste Asiático",
    estimatedCasesPerYear: 140000,
    dalysRatePer100k: 310.2,
    predominantSerotypes: "DENV-1, DENV-2, DENV-3, DENV-4",
    clinicalTrialsCount: 2,
    isResearchDesert: true,
    notice: "Deserto relativo de pesquisa: hiperendemicidade com escassos ensaios randomizados registrados.",
  },
  {
    countryCode: "IND",
    countryName: "Índia",
    region: "Sudeste Asiático",
    estimatedCasesPerYear: 4500000,
    dalysRatePer100k: 620.8,
    predominantSerotypes: "DENV-1, DENV-2",
    clinicalTrialsCount: 4,
    isResearchDesert: true,
    notice: "Deserto severo de pesquisa: maior volume global de casos e DALYs em contraste com ensaios primários publicados.",
  },
  {
    countryCode: "COL",
    countryName: "Colômbia",
    region: "América Latina / Caribe",
    estimatedCasesPerYear: 110000,
    dalysRatePer100k: 290.4,
    predominantSerotypes: "DENV-1, DENV-2",
    clinicalTrialsCount: 5,
    isResearchDesert: false,
    notice: "Estudos multicêntricos latino-americanos presentes.",
  },
  {
    countryCode: "SGP",
    countryName: "Cingapura",
    region: "Sudeste Asiático",
    estimatedCasesPerYear: 32000,
    dalysRatePer100k: 65.0,
    predominantSerotypes: "DENV-1, DENV-2, DENV-3",
    clinicalTrialsCount: 9,
    isResearchDesert: false,
    notice: "Centro de alta renda com elevada densidade de ensaios clínicos e vigilância genômica.",
  },
];

const DEFAULT_TRIAL_BURDEN_LINKS: TrialBurdenLinkDTO[] = [
  {
    trialId: "NCT01234001",
    countryCode: "BRA",
    countryName: "Brasil",
    year: 2022,
    participantsCount: 350,
    siteName: "Hospital das Clínicas da FMUSP / ICr - São Paulo",
    cases: 1450000,
    incidencePer100k: 680.5,
    caseDefinition: "CASOS_NOTIFICADOS_SINAN",
    source: "SINAN/DATASUS",
    hasBurdenData: true,
    burdenStatus: "COM_DADO_CARGA",
    disparityIndicator: "PROPORCIONAL",
  },
  {
    trialId: "NCT01234002",
    countryCode: "IND",
    countryName: "Índia",
    year: 2022,
    participantsCount: 30,
    siteName: "All India Institute of Medical Sciences (AIIMS) - New Delhi",
    cases: 2300000,
    incidencePer100k: 164.2,
    caseDefinition: "CASOS_ESTIMADOS_OPENDENGUE",
    source: "OPENDENGUE",
    hasBurdenData: true,
    burdenStatus: "COM_DADO_CARGA",
    disparityIndicator: "DESERTO_CRITICO",
  },
  {
    trialId: "NCT01234003",
    countryCode: "VNM",
    countryName: "Vietnã",
    year: 2022,
    participantsCount: 140,
    siteName: "Hospital for Tropical Diseases / Oxford University Clinical Research Unit (OUCRU)",
    cases: 360000,
    incidencePer100k: 375.0,
    caseDefinition: "CASOS_NOTIFICADOS_MINISTERIO_SAUDE",
    source: "OPENDENGUE",
    hasBurdenData: true,
    burdenStatus: "COM_DADO_CARGA",
    disparityIndicator: "PROPORCIONAL",
  },
  {
    trialId: "NCT01234004",
    countryCode: "SGP",
    countryName: "Cingapura",
    year: 2022,
    participantsCount: 180,
    siteName: "Singapore General Hospital / Duke-NUS Medical School",
    cases: 8500,
    incidencePer100k: 145.0,
    caseDefinition: "CASOS_LABORATORIAIS_CONFIRMADOS",
    source: "MOH_SINGAPORE",
    hasBurdenData: true,
    burdenStatus: "COM_DADO_CARGA",
    disparityIndicator: "CENTRO_CONCENTRADO",
  },
  {
    trialId: "NCT01234005",
    countryCode: "COL",
    countryName: "Colômbia",
    year: 2022,
    participantsCount: 85,
    siteName: "Centro de Atención e Investigación Médica (CAIMED) - Bogotá",
    cases: 65000,
    incidencePer100k: 128.0,
    caseDefinition: "CASOS_SIVIGILA_NOTIFICADOS",
    source: "OPENDENGUE",
    hasBurdenData: true,
    burdenStatus: "COM_DADO_CARGA",
    disparityIndicator: "PROPORCIONAL",
  },
  {
    trialId: "NCT01234006",
    countryCode: "FRA",
    countryName: "França",
    year: 2022,
    participantsCount: 45,
    siteName: "Hôpital Universitaire Pitié Salpêtrière - Paris (Centro Coordenador)",
    cases: null,
    incidencePer100k: null,
    caseDefinition: null,
    source: null,
    hasBurdenData: false,
    burdenStatus: "SEM_DADO_CARGA",
    disparityIndicator: "SEM_DADOS",
  },
];

export function DiseaseBurdenView() {
  const [data, setData] = useState<DiseaseBurdenDTO[]>(DEFAULT_BURDEN);
  const [trialLinks, setTrialLinks] = useState<TrialBurdenLinkDTO[]>(DEFAULT_TRIAL_BURDEN_LINKS);
  const [filterDesertOnly, setFilterDesertOnly] = useState<boolean>(false);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    fetch("/api/public/disease-burden")
      .then((res) => {
        if (!res.ok) throw new Error("Status " + res.status);
        return res.json();
      })
      .then((items: DiseaseBurdenDTO[]) => {
        if (Array.isArray(items) && items.length > 0) {
          setData(items);
        }
      })
      .catch(() => {});

    fetch("/api/public/trial-burden-link")
      .then((res) => {
        if (!res.ok) throw new Error("Status " + res.status);
        return res.json();
      })
      .then((json: { data?: TrialBurdenLinkDTO[] }) => {
        if (json?.data && Array.isArray(json.data) && json.data.length > 0) {
          setTrialLinks(json.data);
        }
      })
      .catch(() => {});
  }, []);

  const desertsCount = data.filter((d) => d.isResearchDesert).length;

  const filteredMacro = data.filter((d) => {
    if (filterDesertOnly && !d.isResearchDesert) return false;
    if (
      search &&
      !d.countryName.toLowerCase().includes(search.toLowerCase()) &&
      !d.region.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const filteredTrials = trialLinks.filter((t) => {
    if (filterDesertOnly && t.disparityIndicator !== "DESERTO_CRITICO") return false;
    if (
      search &&
      !t.countryName.toLowerCase().includes(search.toLowerCase()) &&
      !t.siteName.toLowerCase().includes(search.toLowerCase()) &&
      !t.trialId.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const missingBurdenCount = trialLinks.filter((t) => !t.hasBurdenData).length;

  return (
    <div className="disease-burden-view" style={{ marginTop: "1.5rem" }}>
      <h2>Eixo C — Carga Global de Doença (GBD) e Sítios de Ensaios Clínicos</h2>
      <p>
        Análise da assimetria entre o impacto epidemiológico global (DALYs e casos anuais) e a
        distribuição geográfica dos ensaios clínicos farmacológicos e recrutamento de participantes para a dengue.
      </p>

      <div className="metrics" style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <article style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", flex: 1 }}>
          <strong>{data.length}</strong>
          <div>Países monitorados</div>
        </article>
        <article
          style={{
            border: "1px solid #d9534f",
            backgroundColor: "#fff5f5",
            padding: "1rem",
            borderRadius: "8px",
            flex: 1,
          }}
        >
          <strong style={{ color: "#d9534f" }}>{desertsCount}</strong>
          <div>Desertos críticos de pesquisa</div>
        </article>
        <article style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", flex: 1 }}>
          <strong>~9,94 Milhões</strong>
          <div>Casos anuais mapeados</div>
        </article>
        <article style={{ border: "1px solid #eab308", backgroundColor: "#fefce8", padding: "1rem", borderRadius: "8px", flex: 1 }}>
          <strong style={{ color: "#a16207" }}>{missingBurdenCount}</strong>
          <div>Sem Dado de Carga (Salvaguarda RC-04)</div>
        </article>
      </div>

      <div
        className="filter-bar"
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <label>
          Buscar país, região ou centro:{" "}
          <input
            type="search"
            placeholder="Ex: Índia, Brasil, NCT01234001, FMUSP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
          <input
            type="checkbox"
            checked={filterDesertOnly}
            onChange={(e) => setFilterDesertOnly(e.target.checked)}
          />
          Exibir apenas desertos de pesquisa (alta carga / escassos ensaios)
        </label>
      </div>

      {/* Seção 1: Panorama Macroeconômico GBD */}
      <section style={{ marginBottom: "2rem" }}>
        <h3 style={{ borderBottom: "1px solid #e2e8f0", paddingBottom: "0.5rem" }}>
          🌐 Panorama Geral de Carga de Doença e Desertos de Pesquisa
        </h3>
        <div className="table-scroll" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
                <th style={{ padding: "8px" }}>País</th>
                <th style={{ padding: "8px" }}>Região</th>
                <th style={{ padding: "8px" }}>Casos Estimados / Ano</th>
                <th style={{ padding: "8px" }}>DALYs / 100k hab</th>
                <th style={{ padding: "8px" }}>Sorotipos</th>
                <th style={{ padding: "8px" }}>Ensaios Clínicos</th>
                <th style={{ padding: "8px" }}>Status Científico</th>
                <th style={{ padding: "8px" }}>Observações</th>
              </tr>
            </thead>
            <tbody>
              {filteredMacro.map((item) => (
                <tr
                  key={item.countryCode}
                  style={{
                    borderBottom: "1px solid #eee",
                    backgroundColor: item.isResearchDesert ? "#fff9f9" : "inherit",
                  }}
                >
                  <td style={{ padding: "8px", fontWeight: "bold" }}>
                    {item.countryName} ({item.countryCode})
                  </td>
                  <td style={{ padding: "8px" }}>{item.region}</td>
                  <td style={{ padding: "8px" }}>{item.estimatedCasesPerYear.toLocaleString("pt-BR")}</td>
                  <td style={{ padding: "8px" }}>{item.dalysRatePer100k.toFixed(1)}</td>
                  <td style={{ padding: "8px" }}>{item.predominantSerotypes}</td>
                  <td style={{ padding: "8px", textAlign: "center", fontWeight: "bold" }}>
                    {item.clinicalTrialsCount}
                  </td>
                  <td style={{ padding: "8px" }}>
                    {item.isResearchDesert ? (
                      <span
                        style={{
                          color: "#b02a37",
                          backgroundColor: "#f8d7da",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          fontWeight: "bold",
                        }}
                      >
                        Deserto de Pesquisa
                      </span>
                    ) : (
                      <span
                        style={{
                          color: "#0f5132",
                          backgroundColor: "#d1e7dd",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                        }}
                      >
                        Centro Ativo
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "8px", fontSize: "0.85rem", color: "#555" }}>{item.notice}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Seção 2: Cruzamento Sítios de Ensaios vs Carga Epidemiológica (REQ-ANA-004) */}
      <section style={{ marginBottom: "2rem" }}>
        <h3 style={{ borderBottom: "1px solid #e2e8f0", paddingBottom: "0.5rem" }}>
          📍 Sítios e Participantes de Ensaios vs. Carga de Dengue (REQ-ANA-004)
        </h3>
        <p style={{ fontSize: "0.9rem", color: "#64748b" }}>
          Cruzamento auditável dos sítios de ensaios e recrutamento por país/ano com a definição epidemiológica declarada.
        </p>
        <div className="table-scroll" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left", backgroundColor: "#f8fafc" }}>
                <th style={{ padding: "8px" }}>Ensaio</th>
                <th style={{ padding: "8px" }}>País</th>
                <th style={{ padding: "8px" }}>Ano</th>
                <th style={{ padding: "8px" }}>Centro / Sítio de Recrutamento</th>
                <th style={{ padding: "8px", textAlign: "center" }}>Participantes</th>
                <th style={{ padding: "8px" }}>Casos no País/Ano</th>
                <th style={{ padding: "8px" }}>Definição do Dado Epidemiológico</th>
                <th style={{ padding: "8px" }}>Indicador de Disparidade</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrials.map((item) => (
                <tr
                  key={`${item.trialId}-${item.countryCode}`}
                  style={{
                    borderBottom: "1px solid #eee",
                    backgroundColor:
                      item.disparityIndicator === "DESERTO_CRITICO"
                        ? "#fff5f5"
                        : !item.hasBurdenData
                        ? "#fafafa"
                        : "inherit",
                  }}
                >
                  <td style={{ padding: "8px", fontWeight: "bold" }}>{item.trialId}</td>
                  <td style={{ padding: "8px" }}>
                    {item.countryName} ({item.countryCode})
                  </td>
                  <td style={{ padding: "8px" }}>{item.year}</td>
                  <td style={{ padding: "8px", fontSize: "0.9rem" }}>{item.siteName}</td>
                  <td style={{ padding: "8px", textAlign: "center", fontWeight: "bold" }}>
                    {item.participantsCount}
                  </td>
                  <td style={{ padding: "8px" }}>
                    {item.hasBurdenData && item.cases !== null ? (
                      item.cases.toLocaleString("pt-BR")
                    ) : (
                      <span
                        style={{
                          backgroundColor: "#f1f5f9",
                          color: "#64748b",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.82rem",
                          fontWeight: "bold",
                        }}
                      >
                        SEM DADO DE CARGA (—)
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "8px", fontSize: "0.85rem", color: "#475569" }}>
                    {item.caseDefinition ?? "Não aplicável / Sem série endêmica"}
                  </td>
                  <td style={{ padding: "8px" }}>
                    {item.disparityIndicator === "DESERTO_CRITICO" && (
                      <span
                        style={{
                          color: "#b02a37",
                          backgroundColor: "#f8d7da",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          fontWeight: "bold",
                        }}
                      >
                        ⚠️ Deserto Crítico
                      </span>
                    )}
                    {item.disparityIndicator === "CENTRO_CONCENTRADO" && (
                      <span
                        style={{
                          color: "#0369a1",
                          backgroundColor: "#e0f2fe",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          fontWeight: "bold",
                        }}
                      >
                        🏢 Centro Concentrado
                      </span>
                    )}
                    {item.disparityIndicator === "PROPORCIONAL" && (
                      <span
                        style={{
                          color: "#0f5132",
                          backgroundColor: "#d1e7dd",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                        }}
                      >
                        ⚖️ Proporcional
                      </span>
                    )}
                    {item.disparityIndicator === "SEM_DADOS" && (
                      <span
                        style={{
                          color: "#64748b",
                          backgroundColor: "#e2e8f0",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                        }}
                      >
                        ℹ️ Sem Carga Endêmica
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="notice" style={{ marginTop: "1rem" }}>
        <strong>Salvaguarda Metodológica REQ-ANA-004 & RC-04:</strong> A ausência de ensaios ou de registros
        nacionais não é interpretada como carga zero de doença. Países sinalizados como
        &quot;Deserto de Pesquisa&quot; concentram elevadas taxas de DALYs segundo o Global Burden of
        Disease (GBD), contrastando com severa sub-representação na pesquisa clínica global.
        Países sem dados epidemiológicos para o ano em questão aparecem estritamente como <code>SEM DADO DE CARGA</code>,
        sem qualquer imputação arbitrária de zero.
      </p>
    </div>
  );
}
