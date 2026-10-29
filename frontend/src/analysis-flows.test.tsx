import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth/AuthContext";
import { AnalysisPanel } from "./pages/AnalysisPanel";
import { OperationalPanelPage } from "./pages/OperationalPanelPage";

const filters={substance:"Drug A",context:"HUMANO",purpose:null,design:null,phase:null,serotype:null};
function auth(roles:string[]) { sessionStorage.setItem("dp.session",JSON.stringify({token:"analysis-token",email:"test@x.org",roles})); }
afterEach(()=>{sessionStorage.clear();vi.unstubAllGlobals();vi.restoreAllMocks();});

it("leitor consulta sem gerar; operacao nao oferece experimento v1",async()=>{
  auth(["LEITOR"]);
  vi.stubGlobal("fetch",vi.fn(async()=>new Response("[]")));
  const view=render(<AuthProvider><AnalysisPanel filters={filters}/></AuthProvider>);
  expect(await screen.findByText("Nenhuma análise solicitada.")).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"Gerar análise descritiva"})).not.toBeInTheDocument();
  view.unmount();auth(["ADMINISTRADOR"]);
  vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({jobs:[],outbox:[],reassessments:[]}))));
  render(<AuthProvider><OperationalPanelPage/></AuthProvider>);
  await screen.findByText("Nenhum job registrado.");
  expect(screen.queryByRole("button",{name:/Particionar|Kappa|Experimento/})).not.toBeInTheDocument();
});

it("pesquisador solicita snapshot com filtros e acompanha estado pendente",async()=>{
  auth(["PESQUISADOR"]);
  const run={id:"a1",status:"PENDING",study_count:2,input_hash:"hash",created_at:"2026-10-27",artifacts:[]};
  let created=false;
  const fetchMock=vi.fn(async(path:string,init?:RequestInit)=>{
    if (init?.method==="POST") created=true;
    return new Response(JSON.stringify(init?.method==="POST"||path.endsWith("a1")?run:created?[run]:[]));
  });
  vi.stubGlobal("fetch",fetchMock);
  render(<AuthProvider><AnalysisPanel filters={filters}/></AuthProvider>);
  await userEvent.click(screen.getByRole("button",{name:"Gerar análise descritiva"}));
  expect(await screen.findByRole("status")).toHaveTextContent("PENDING");
  expect(screen.getByRole("button",{name:"Baixar entrada JSON"})).toBeInTheDocument();
  const call=fetchMock.mock.calls.find(([,init])=>init?.method==="POST");
  expect(call?.[0]).toBe("/api/analyses");
  expect(JSON.parse(call![1]!.body as string)).toEqual(filters);
});

it("analise vazia mostra sem dados e nao transforma proporcao nula em cem por cento",async()=>{
  auth(["LEITOR"]);
  const run={id:"a1",status:"COMPLETED",study_count:0,input_hash:"hash",created_at:"2026-10-27",artifacts:[{name:"summary.json"},{name:"bundle.zip"}]};
  const result={status:"NO_DATA",studyCount:0,documentCount:0,reassessmentPendingCount:0,notice:"Corpus filtrado; nao estima eficacia.",contextCounts:[],distributions:[],completeness:[],gaps:[],traceability:[{metric:"versions",numerator:0,denominator:0,proportion:null}]};
  vi.stubGlobal("fetch",vi.fn(async(path:string)=>new Response(JSON.stringify(path.includes("artifacts")?result:path.endsWith("a1")?run:[run]))));
  render(<AuthProvider><AnalysisPanel filters={filters}/></AuthProvider>);
  await userEvent.click(await screen.findByRole("button",{name:"Consultar análise"}));
  expect(await screen.findByText("Sem dados para os filtros selecionados.")).toBeInTheDocument();
  expect(screen.queryByText("100.0%")).not.toBeInTheDocument();
  expect(screen.getByText("Rastreabilidade estrutural",{selector:"h4"})).toBeInTheDocument();
});

it("mostra conflitos, pendencias e falhas de download sem enviar usuario a URL sem token",async()=>{
  auth(["PESQUISADOR"]);
  const run={id:"a1",status:"COMPLETED",study_count:2,input_hash:"hash",created_at:"2026-10-27",artifacts:[]};
  const result={status:"COMPLETE",studyCount:2,documentCount:3,reassessmentPendingCount:1,notice:"Aviso",contextCounts:[],distributions:[{field:"phase",category:"[CONFLITO]",status:"CONFLITO",count:1,denominator:2,proportion:0.5}],completeness:[],gaps:[],traceability:[]};
  const fetchMock=vi.fn(async(path:string)=>path.includes("bundle.zip")?new Response(null,{status:503}):new Response(JSON.stringify(path.includes("artifacts")?result:path.endsWith("a1")?run:[run])));
  vi.stubGlobal("fetch",fetchMock);
  render(<AuthProvider><AnalysisPanel filters={filters}/></AuthProvider>);
  await userEvent.click(await screen.findByRole("button",{name:"Consultar análise"}));
  expect(await screen.findByText("[CONFLITO]")).toBeInTheDocument();
  expect(screen.getByText(/1 estudos com reavaliação pendente/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button",{name:"Baixar pacote ZIP"}));
  await waitFor(()=>expect(screen.getByRole("alert")).toHaveTextContent("503"));
  expect(fetchMock).toHaveBeenCalledWith("/api/analyses/a1/artifacts?name=bundle.zip",{headers:{Authorization:"Bearer analysis-token"}});
});
