"""Comandos reproduziveis para coleta, analise, publicacao e download do corpus."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .runtime import load_env

# Busca sensivel: vacinas sao excluidas por triagem, evitando perder estudos mistos.
PUBMED_QUERY = ('(dengue[MeSH Terms] OR dengue[Title/Abstract]) AND '
                '(drug therapy[Subheading] OR therapeutics[MeSH Terms] OR antiviral agents[MeSH Terms] '
                'OR pharmacolog*[Title/Abstract] OR drug*[Title/Abstract] OR compound*[Title/Abstract] '
                'OR treatment*[Title/Abstract] OR therapeutic*[Title/Abstract] OR prophylax*[Title/Abstract])')


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.token = None

    def call(self, path, body=None, binary=False):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token: headers["Authorization"] = "Bearer " + self.token
        try:
            with urlopen(Request(self.base + path, data=data, headers=headers), timeout=90) as response:
                content = response.read()
        except HTTPError as error:
            # Nao imprimir corpo ou cabecalhos que possam conter credenciais.
            raise RuntimeError(f"API retornou HTTP {error.code} em {path.split('?')[0]}") from None
        return content if binary else json.loads(content) if content else None

    def login(self):
        email = os.environ.get("DENGUEPHARMA_RESEARCH_EMAIL") or os.environ.get("BOOTSTRAP_ADMIN_EMAIL")
        password = os.environ.get("DENGUEPHARMA_RESEARCH_PASSWORD") or os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not email or not password: raise ValueError("Configure as credenciais de pesquisador no ambiente")
        self.token = self.call("/api/auth/login", {"email": email, "password": password})["token"]


def wait_for(client, path, timeout=1800):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = client.call(path)
        if run["status"] == "COMPLETED": return run
        if run["status"] in {"FAILED", "QUARANTINED"}: raise RuntimeError("Execucao falhou; consulte a area operacional para retomar")
        time.sleep(2)
    raise TimeoutError("Execucao continua pendente; use seu identificador para acompanhar ou retomar")


def validate_pilot(review_path, dataset_path):
    """Exige revisao humana completa do piloto real, sem aceitar arquivo de outro corpus."""
    snapshot = json.loads(Path(dataset_path).read_bytes())
    from .corpus import prepare
    records, _, _ = prepare(snapshot)
    expected = {r["document_id"] for r in records[:50]}
    if not expected or snapshot.get("protocol", {}).get("maxRecordsPerSource", 0) <= 0:
        raise ValueError("Informe um snapshot de piloto nao vazio")
    with Path(review_path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(expected) or {r.get("document_id") for r in rows} != expected:
        raise ValueError("A planilha deve corresponder a todos os documentos do piloto")
    for row in rows:
        if row.get("preparation_validated") != "SIM" or row.get("eligibility_decision") not in {"INCLUIR", "EXCLUIR"} or not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
            raise ValueError("Revisao humana pendente: validar preparacao, elegibilidade, revisor e data")
        if row["eligibility_decision"] == "EXCLUIR" and not row.get("exclusion_reason", "").strip():
            raise ValueError("Informe motivo de exclusao")
    return {"pilotInputHash": hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest(),
            "reviewHash": hashlib.sha256(Path(review_path).read_bytes()).hexdigest(), "reviewedRecords": len(rows)}


def collect(client, stage, cutoff, review=None, pilot=None):
    validation = validate_pilot(review, pilot) if stage == "full" else None
    code = f"DS3-{stage.upper()}-{datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%Y%m%d-%H%M%S')}"
    strategy = {"pubmed": {"query": PUBMED_QUERY}, "clinicaltrials": {"condition": "Dengue"}, "maxRecords": 25 if stage == "pilot" else 0}
    eligibility = {"stage": stage, "include": ["medicamentos", "compostos", "clinico", "pre-clinico"],
                   "exclude": ["vacinas", "controle vetorial", "diagnostico sem intervencao farmacologica"],
                   "screeningRequired": True, "pilotValidation": validation,
                   "sampling": "primeiros 25 registros retornados por fonte; amostra de conveniencia, nao representativa" if stage == "pilot" else "busca completa segundo estrategia registrada"}
    protocol = client.call("/api/protocols", {"code": code, "title": "DenguePharma: revisao de escopo e panorama farmacologico",
        "question": "Quais medicamentos e compostos sao estudados para dengue, em quais contextos e com qual cobertura documental?",
        "sources": ["PUBMED", "CLINICALTRIALS"], "strategy": strategy, "eligibility": eligibility, "cutoffDate": cutoff})
    client.call(f"/api/protocols/{protocol['id']}/register", {})
    imports = []
    for source in ("PUBMED", "CLINICALTRIALS"):
        run = client.call("/api/imports", {"protocolId": protocol["id"], "source": source})
        print(f"Coleta {source}: {run['runId']}", flush=True)
        result = wait_for(client, f"/api/imports/{run['runId']}")
        imports.append({"id": run["runId"], "source": source, "recordsSeen": result["records_seen"], "status": result["status"]})
    return {"protocolId": protocol["id"], "stage": stage, "cutoff": cutoff, "imports": imports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--base-url", default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    collection = commands.add_parser("collect")
    collection.add_argument("--stage", choices=("pilot", "full"), default="pilot")
    collection.add_argument("--cutoff", default=datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat())
    collection.add_argument("--review-csv"); collection.add_argument("--pilot-dataset")
    collection.add_argument("--output", required=True)
    analysis = commands.add_parser("analyze"); analysis.add_argument("--protocol", required=True)
    analysis.add_argument("--previous"); analysis.add_argument("--output", required=True)
    publication = commands.add_parser("publish"); publication.add_argument("--analysis", required=True)
    download = commands.add_parser("download"); download.add_argument("--analysis", required=True); download.add_argument("--output", required=True)
    args = parser.parse_args()
    if Path(args.env_file).exists(): load_env(args.env_file)
    client = Client(args.base_url or os.environ.get("BACKEND_URL", "http://127.0.0.1:8080"))
    client.login()
    if args.command == "collect":
        if args.stage == "full" and not (args.review_csv and args.pilot_dataset): parser.error("coleta completa exige --review-csv e --pilot-dataset")
        result = collect(client, args.stage, args.cutoff, args.review_csv, args.pilot_dataset)
    elif args.command == "analyze":
        result = client.call("/api/analyses/corpus", {"protocolId": args.protocol, "previousAnalysisId": args.previous})
        print(f"Analise: {result['id']}", flush=True)
        result = wait_for(client, f"/api/analyses/{result['id']}")
    elif args.command == "publish":
        result = client.call(f"/api/analyses/{args.analysis}/publish", {})
    else:
        folder = Path(args.output); folder.mkdir(parents=True, exist_ok=True)
        for name in ("dataset.json", "bundle.zip", "summary.json", "pilot_review.csv"):
            (folder / name).write_bytes(client.call(f"/api/analyses/{args.analysis}/artifacts?name={name}", binary=True))
        print(f"Artefatos salvos em {folder}")
        return
    if getattr(args, "output", None):
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k in {"id", "protocolId", "status", "published", "stage"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
