"""Ponte temporaria para coletores duraveis existentes. Piloto clinico novo, ate 20 registros."""
from datetime import date
import json
import os
from pathlib import Path
import time
from urllib.request import Request,urlopen
from uuid import uuid4

from ..domain import digest,json_bytes


class Client:
    def __init__(self):
        self.base=os.getenv("ANALYTICS_AUTH_URL","http://127.0.0.1:18080").rstrip("/")
        self.token=None

    def call(self,path,body=None,binary=False):
        headers={"Content-Type":"application/json"}
        if self.token: headers["Authorization"]="Bearer "+self.token
        request=Request(self.base+path,headers=headers,data=json_bytes(body) if body is not None else None)
        with urlopen(request,timeout=30) as response: data=response.read()
        return data if binary else json.loads(data) if data else None

    def login(self):
        email=os.getenv("DENGUEPHARMA_RESEARCH_EMAIL") or os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        password=os.getenv("DENGUEPHARMA_RESEARCH_PASSWORD") or os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if not email or not password: raise ValueError("RESEARCH_CREDENTIALS_REQUIRED")
        self.token=self.call("/api/auth/login",dict(email=email,password=password))["token"]


def wait(client,path):
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        result=client.call(path)
        if result["status"]=="COMPLETED": return result
        if result["status"] in {"FAILED","QUARANTINED"}: raise RuntimeError("COLLECTION_FAILED_RESUME_IN_LEGACY")
        time.sleep(2)
    raise TimeoutError("COLLECTION_PENDING_USE_SAVED_CHECKPOINT")


def collect(protocol,cutoff,folder: Path,client=None):
    date.fromisoformat(cutoff)
    if date.fromisoformat(cutoff)>date.today(): raise ValueError("FUTURE_CUTOFF")
    client=client or Client(); client.login(); folder.mkdir(parents=True,exist_ok=True)
    path=folder/"checkpoint.json"
    config={"clinical_protocol_hash":digest(json_bytes(protocol)),"cutoff":cutoff,"limit_per_source":10}
    state=json.loads(path.read_bytes()) if path.exists() else {"configuration":config,"code":"CLINICAL-CALIBRATION-"+str(uuid4()),"imports":{}}
    if state["configuration"]!=config: raise ValueError("CALIBRATION_CONFIGURATION_CHANGED_CREATE_NEW_FOLDER")
    def save():
        temporary=folder/"checkpoint.tmp"; temporary.write_bytes(json_bytes(state)); temporary.replace(path)
    save()
    if "protocol_id" not in state:
        strategy={"pubmed":{"query":protocol["search"]["pubmed"]},"clinicaltrials":{"condition":"Dengue"},"maxRecords":10}
        result=client.call("/api/protocols",dict(code=state["code"],title="Calibracao clinica: dengue estabelecida",question=protocol["question"],sources=["PUBMED","CLINICALTRIALS"],strategy=strategy,eligibility={"stage":"CALIBRACAO_CLINICA","clinicalProtocolHash":config["clinical_protocol_hash"],"selectionRequired":True,"include":protocol["population"],"exclude":protocol["contexts_excluded"],"sampling":"Primeiros 10 resultados por fonte; conveniencia, sem revisao automatica; nao e busca completa nem referencia adjudicada"},cutoffDate=cutoff))
        state["protocol_id"]=result["id"]; save()
    if not state.get("registered"):
        client.call(f'/api/protocols/{state["protocol_id"]}/register',{}); state["registered"]=True; save()
    for source in ("PUBMED","CLINICALTRIALS"):
        if source not in state["imports"]:
            state["imports"][source]=client.call("/api/imports",dict(protocolId=state["protocol_id"],source=source))["runId"]; save()
        wait(client,f'/api/imports/{state["imports"][source]}')
    if "analysis_id" not in state:
        state["analysis_id"]=client.call("/api/analyses/corpus",dict(protocolId=state["protocol_id"]))["id"]; save()
    wait(client,f'/api/analyses/{state["analysis_id"]}')
    content=client.call(f'/api/analyses/{state["analysis_id"]}/artifacts?name=dataset.json',binary=True)
    target=folder/"dataset.json"
    if target.exists() and target.read_bytes()!=content: raise ValueError("IMMUTABLE_CALIBRATION_DATASET")
    target.write_bytes(content)
    state["input_hash"]=digest(content); state["status"]="COLLECTED_PENDING_INDEPENDENT_REVIEW"; save()
    return state
