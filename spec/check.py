"""Verifica rastreabilidade e evidencias sem confundir cenario escrito com teste executado."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def validate(root=ROOT):
    data = json.loads((root / "requirements.json").read_text(encoding="utf-8"))
    requirements = data["requirements"]; ids = set()
    for r in requirements:
        if not re.fullmatch(r"REQ-[A-Z]+-\d{3}", r["id"]) or r["id"] in ids: raise ValueError("ID invalido/duplicado")
        ids.add(r["id"])
        for name in ("statement", "acceptance", "scenario", "research", "task", "verification", "priority", "state"):
            if not r.get(name): raise ValueError(r["id"]+": campo ausente "+name)
        if r["state"] not in {"planejado", "parcial", "implementado", "verificado"}: raise ValueError("Estado invalido")
        if r["task"] not in {f"M{i:02d}" for i in range(9)}: raise ValueError("Tarefa inexistente")
        if r["state"] == "verificado" and not r["tests"]: raise ValueError("Verificacao sem teste")
    with (root / "rastreabilidade.csv").open(encoding="utf-8", newline="") as stream: rows = list(csv.DictReader(stream))
    if len(rows) != len(ids) or {r["requirement"] for r in rows} != ids: raise ValueError("Matriz com IDs divergentes")
    for row in rows:
        item = next(r for r in requirements if r["id"] == row["requirement"])
        if any(row[k] != item[k] for k in ("state", "scenario", "task", "priority", "verification", "research")) or row["tests"] != ";".join(item["tests"]):
            raise ValueError("Matriz divergente: "+item["id"])
    if len([r for r in requirements if not r["id"].startswith(("REQ-MIG-","REQ-CLN-"))]) != 66: raise ValueError("Catalogo PDF incompleto")
    return data


def junit_evidence(path, known_ids):
    passed = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        props = {p.attrib["name"]: p.attrib["value"] for p in case.findall("properties/property")}
        reqs = props.get("requirements", "").split(",") if props.get("requirements") else []
        if any(key not in known_ids for key in reqs): raise ValueError("Teste cita requisito inexistente")
        if case.find("failure") is not None or case.find("error") is not None or case.find("skipped") is not None: continue
        for key in reqs: passed.setdefault(key, set()).add(case.attrib["name"].split("[")[0])
    return passed


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--junit", type=Path); parser.add_argument("--verify-foundation", action="store_true"); parser.add_argument("--verify-clinical",action="store_true"); parser.add_argument("--release-all", action="store_true")
    args = parser.parse_args(); data = validate(); ids = {r["id"] for r in data["requirements"]}
    passed = junit_evidence(args.junit, ids) if args.junit else {}
    if args.release_all:
        missing = [r["id"] for r in data["requirements"] if r["priority"] == "M" and (r["state"] != "verificado" or not r["tests"] or not set(r["tests"]) <= passed.get(r["id"], set()))]
        if missing: raise ValueError("Release completo bloqueado; requisitos obrigatorios pendentes: "+", ".join(missing))
    if args.verify_foundation or args.verify_clinical:
        for r in data["requirements"]:
            if (args.verify_foundation and r["id"].startswith("REQ-MIG-")) or (args.verify_clinical and r["id"].startswith("REQ-CLN-") and r["tests"]):
                if not set(r["tests"]) <= passed.get(r["id"], set()): raise ValueError("Teste aprovado ausente: "+r["id"])
                r["state"] = "verificado"
        (ROOT / "requirements.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        with (ROOT / "rastreabilidade.csv").open("w", encoding="utf-8", newline="") as f:
            writer=csv.DictWriter(f,fieldnames=["requirement","research","task","scenario","verification","priority","state","tests"]);writer.writeheader()
            for r in data["requirements"]: writer.writerow({"requirement":r["id"],**{k:r[k] for k in ("research","task","scenario","verification","priority","state")},"tests":";".join(r["tests"])})
    elif args.junit:
        for r in data["requirements"]:
            if r["state"] == "verificado" and not set(r["tests"]) <= passed.get(r["id"], set()): raise ValueError("Verificacao sem evidencia aprovada: "+r["id"])
    print(f'SDD: {len(ids)} requisitos; {len(passed)} com evidencia automatizada nesta execucao. Requisitos futuros permanecem planejados.')


if __name__ == "__main__": main()
