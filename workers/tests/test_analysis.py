import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from denguepharma_workers.analysis import FIELDS, STATES, analyze, bundle, digest


def study(id_, context="HUMANO", **fields):
    return {"studyId": id_, "context": context, "purpose": "TRATAMENTO", "reassessmentPending": False,
            "fields": {field: fields.get(field, {"status":"SEM_REVISAO"}) for field in FIELDS}, "references": []}


def content(studies):
    return json.dumps({"schemaVersion":"2.0","dictionaryVersion":"descriptive-v2.0","fields":FIELDS,"studies":studies},ensure_ascii=False).encode()


def present(value): return {"status":"PRESENTE","value":value}


def test_contagens_conhecidas_e_estudos_duplicados_nao_inflam_denominadores():
    first=study("a", substance=present("Drug A"),phase=present("2"),serotype=present("DENV-2"),outcome_category=present("CLINICO"))
    second=study("b",substance=present("Drug A"),phase={"status":"NAO_APLICAVEL"},serotype=present("DENV-2"))
    third=study("c","IN_VITRO",substance=present("Drug B"),phase={"status":"NAO_APLICAVEL"})
    summary,_=analyze(content([first,copy.deepcopy(first),second,third]))
    assert summary["studyCount"]==3
    row=next(r for r in summary["distributions"] if r["context"]=="HUMANO" and r["field"]=="serotype")
    assert row["count"]==2 and row["denominator"]==2 and row["proportion"]==1
    phase=next(r for r in summary["completeness"] if r["context"]=="HUMANO" and r["field"]=="phase")
    assert phase["present"]==1 and phase["applicable"]==1 and phase["total"]==2
    preclinical=next(r for r in summary["completeness"] if r["context"]=="IN_VITRO" and r["field"]=="phase")
    assert preclinical["applicable"]==0 and preclinical["proportion"] is None
    zero=next(r for r in summary["gaps"] if r["context"]=="HUMANO" and r["substance"]=="Drug A" and r["category"]=="VIROLOGICO")
    assert zero["count"]==0


def test_todos_estados_preservados_sem_converter_ausencia_em_zero():
    studies=[study(str(i),design=present("RCT") if state=="PRESENTE" else {"status":state}) for i,state in enumerate(STATES)]
    summary,_=analyze(content(studies))
    row=next(r for r in summary["completeness"] if r["field"]=="design")
    assert row["states"]=={state:1 for state in STATES}
    assert row["present"]==1 and row["applicable"]==7 and row["proportion"]==pytest.approx(1/7)
    assert any(r["status"]=="CONFLITO" for r in summary["distributions"])


def test_sem_dados_nao_inventa_metricas_perfeitas():
    summary,_=analyze(content([]))
    assert summary["status"]=="NO_DATA" and summary["studyCount"]==0
    assert not summary["completeness"] and not summary["gaps"]
    assert all(row["proportion"] is None for row in summary["traceability"])
    files=bundle(content([]))
    assert b"Sem dados" in files["report.html"]


def test_referencias_documentais_sem_contar_duas_vezes_mesmo_campo():
    first=study("a",design=present("RCT"))
    ref={"fieldId":"f1","field":"design","documentId":"d1","documentVersionId":"v1","absenceStatus":"PRESENTE",
         "hasIdentifier":True,"hasVersion":True,"hasLocator":False}
    first["references"]=[ref,copy.deepcopy(ref)]
    first["reassessmentPending"]=True
    summary,_=analyze(content([first]))
    assert summary["documentCount"]==1 and summary["reassessmentPendingCount"]==1
    by_name={r["metric"]:r for r in summary["traceability"]}
    assert by_name["versions"]["numerator"]==1 and by_name["versions"]["denominator"]==1
    assert by_name["locators"]["proportion"]==0


def test_pacote_tem_tabelas_graficos_manifesto_e_html_escapado():
    source=content([study("a",substance=present("<script>alert(1)</script>"),design=present("RCT"))])
    files=bundle(source)
    manifest=json.loads(files["manifest.json"])
    assert manifest["inputHash"]==digest(source)
    assert all(digest(files[name])==hash_ for name,hash_ in manifest["artifacts"].items())
    assert any(name.endswith(".png") for name in files)
    assert b"<script>" not in files["report.html"]
    with zipfile.ZipFile(io.BytesIO(files["bundle.zip"])) as archive:
        assert archive.read("dataset.json")==source
        assert "gaps.csv" in archive.namelist()


def test_cli_e_worker_compartilham_mesmos_resultados(tmp_path):
    source=content([study("a",design=present("RCT"))])
    path=tmp_path/"input.json"; path.write_bytes(source)
    result=subprocess.run([sys.executable,"-m","denguepharma_workers.analysis","--input",str(path),"--output",str(tmp_path/"output")],capture_output=True,timeout=60)
    assert result.returncode==0,result.stderr.decode()
    files=bundle(source)
    assert (tmp_path/"output"/"summary.json").read_bytes()==files["summary.json"]
    assert (tmp_path/"output"/"completeness.csv").read_bytes()==files["completeness.csv"]


def test_schemas_estranhos_e_duplicatas_conflitantes_sao_rejeitados():
    with pytest.raises(ValueError): analyze(b'{"schemaVersion":"1"}')
    with pytest.raises(ValueError,match="duplicado"):
        analyze(content([study("a",design=present("RCT")),study("a",design=present("COORTE"))]))
