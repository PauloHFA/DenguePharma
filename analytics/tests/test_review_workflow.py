import csv
from io import BytesIO,StringIO
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.review import package,parse,import_csv,progress,locator,LocatorRequest,COLUMNS,HUMAN_COLUMNS
from denguepharma_analytics.clinical.screening_ui import DEFAULTS
from denguepharma_analytics.clinical.workspace import create
from denguepharma_analytics.domain import digest

R1=Principal("independent-one",("PESQUISADOR",))
R2=Principal("independent-two",("PESQUISADOR",))
ADMIN=Principal("independent-third",("ADMINISTRADOR",))


@pytest.fixture
def workspace(tmp_path,snapshot):
    protocol=json.loads((Path(__file__).resolve().parents[2]/"spec/clinical/protocolo.json").read_bytes())
    return create(tmp_path,snapshot,protocol)


def template(workspace):
    with ZipFile(BytesIO(package(workspace,R1))) as archive:
        return list(csv.DictReader(StringIO(archive.read("screening_template.csv").decode())))


def complete(row,decision="EXCLUIR",reason="Synthetic independent source review"):
    return {**row,**DEFAULTS,"decision":decision,"interventions_json":"[]","reason":reason}


def content(rows):
    stream=StringIO(newline=""); writer=csv.DictWriter(stream,fieldnames=COLUMNS,lineterminator="\n");writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode()


def events(workspace):
    with workspace.transaction() as db: return workspace.events(db)


@pytest.mark.requirement("REQ-CLN-008")
def test_blind_package_is_reproducible_and_has_no_private_text(workspace):
    first=package(workspace,R1); assert first==package(workspace,R2)
    with ZipFile(BytesIO(first)) as archive:
        manifest=json.loads(archive.read("manifest.json"))
        assert manifest["studies"]==2 and manifest["input_hash"]==workspace.input.input_hash
        for name,expected in manifest["artifacts"].items(): assert digest(archive.read(name))==expected
        all_content=b"".join(archive.read(n) for n in archive.namelist())
        assert b"PRIVATE_FULLTEXT" not in all_content and b"PRIVATE_CONTACT" not in all_content
    rows=template(workspace)
    assert all(not row[key] for row in rows for key in HUMAN_COLUMNS)
    import_csv(workspace,content([complete(rows[0])]),R1)
    assert all(not row[key] for row in template(workspace) for key in HUMAN_COLUMNS)
    with ZipFile(BytesIO(package(workspace,R2))) as archive:
        assert R1.id.encode() not in b"".join(archive.read(n) for n in archive.namelist())


@pytest.mark.requirement("REQ-CLN-008")
def test_csv_import_is_atomic_idempotent_and_preserves_independence(workspace):
    rows=template(workspace)
    bad=[complete(rows[0]),dict(complete(rows[1]),basis_hash="f"*64)]
    with pytest.raises(ValueError,match="STALE"): import_csv(workspace,content(bad),R1)
    assert events(workspace)==[]
    decisions=[complete(r) for r in rows]
    assert import_csv(workspace,content(decisions),R1)["imported"]==2
    assert import_csv(workspace,content(decisions),R1)["unchanged"]==2 and len(events(workspace))==2
    assert progress(workspace,R1)["missing_independent_votes"]==2
    # A distinct identity submits its own independently written reasons in this fixture.
    second=[complete(r,reason="Second synthetic reviewer independently checked material") for r in rows]
    assert import_csv(workspace,content(second),R2)["imported"]==2
    state=progress(workspace,R2)
    assert state["selection_complete"] is True and state["calibration_approved"] is False
    assert state["approved_results"]==0 and state["next_step"]=="DOCUMENTAR_CALIBRACAO"
    assert {e["actor"] for e in events(workspace)}=={R1.id,R2.id}
    with pytest.raises(ValueError,match="TWO_REVIEWERS"): import_csv(workspace,content(decisions),ADMIN)


@pytest.mark.requirement("REQ-CLN-008")
def test_csv_rejects_incomplete_foreign_and_duplicate_decisions(workspace):
    rows=template(workspace)
    with pytest.raises(ValueError,match="NO_COMPLETED"): parse(content(rows))
    with pytest.raises(ValueError,match="INVALID_HUMAN"): parse(content([dict(rows[0],reason="Partially filled")]))
    with pytest.raises(ValueError,match="DUPLICATE"): parse(content([complete(rows[0]),complete(rows[0])]))
    with pytest.raises(ValueError,match="HEADERS"): parse(b"actor,roles\nhuman,ADMINISTRADOR\n")
    with pytest.raises(ValueError,match="TOO_LARGE"): parse(b"x"*(1024*1024+1))
    for field in ("input_hash","protocol_hash","workspace_id"):
        with pytest.raises(ValueError,match="MISMATCH"): import_csv(workspace,content([dict(complete(rows[0]),**{field:"foreign"})]),R1)
    assert events(workspace)==[]
    result=import_csv(workspace,content([complete(rows[0]),rows[1]]),R1)
    assert result["imported"]==1 and result["skipped"]==1


@pytest.mark.requirement("REQ-CLN-008")
def test_uncertain_votes_do_not_mark_calibration_ready_and_sources_invalidate(workspace):
    rows=template(workspace); decisions=content([complete(r,decision="INCERTO") for r in rows])
    import_csv(workspace,decisions,R1);import_csv(workspace,decisions,R2)
    state=progress(workspace,R1)
    assert state["missing_independent_votes"]==0 and state["unresolved_studies"]==2 and not state["selection_complete"]
    workspace.attach_source(workspace.input.data["documents"][0],"New source representation")
    with pytest.raises(ValueError,match="STALE"): import_csv(workspace,decisions,R1)
    assert progress(workspace,R1)["missing_independent_votes"]==2


@pytest.mark.requirement("REQ-CLN-003")
def test_literal_locator_preserves_unicode_whitespace_and_does_not_approve(workspace):
    text="á😀\n 10/100 participantes"
    version=workspace.attach_source(workspace.input.data["documents"][0],text)
    start=text.index(" 10"); end=start+3
    request=LocatorRequest(version_id=version,field="treatment.events",start=start,end=end)
    value=locator(workspace,request,R1)
    assert value["reference"]["quote"]==" 10"
    assert value["reference"]["text_hash"]==digest(text.encode())
    assert value["document_id"]==workspace.input.data["documents"][0]["documentId"]
    with pytest.raises(ValueError,match="OUT_OF_BOUNDS"): locator(workspace,request.model_copy(update=dict(end=len(text)+1)),R1)
    with pytest.raises(ValueError): LocatorRequest(version_id=version,field="n",start=True,end=4)
    assert events(workspace)==[]


@pytest.mark.requirement("REQ-CLN-008")
def test_review_routes_require_role_and_create_only_screening_events(workspace,tmp_path):
    actors={"one":R1,"reader":Principal("reader",("LEITOR",))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token])); prefix=f"/api/clinical/{workspace.key}"
    rows=template(workspace); data=content([complete(rows[0])]); auth={"Authorization":"Bearer one"}
    for suffix in ("/progress","/review-package"):
        assert app.get(prefix+suffix).status_code==401
        assert app.get(prefix+suffix,headers={"Authorization":"Bearer reader"}).status_code==403
    response=app.get(prefix+"/review-package",headers=auth)
    assert response.status_code==200 and response.content==package(workspace,R1) and response.headers["cache-control"]=="no-store"
    headers={**auth,"Content-Type":"text/csv"}
    assert app.post(prefix+"/screening/import",headers=headers,content=data).json()["imported"]==1
    assert app.post(prefix+"/screening/import",headers=headers,content=data).json()["unchanged"]==1
    assert app.get(prefix+"/progress",headers=auth).json()["calibration_approved"] is False
    assert app.post(prefix+"/screening/import",headers=headers,content=b"invalid").status_code==409
    assert all(e["kind"]=="SCREENED" for e in events(workspace))
    version=workspace.private_state(R1)["sources"][0]["version_id"]
    ref=app.post(prefix+"/locators",headers=auth,json=dict(version_id=version,field="population",start=0,end=1))
    assert ref.status_code==200 and len(ref.json()["reference"]["quote"])==1
    assert app.post(prefix+"/locators",json=dict(version_id=version,field="n",start=0,end=1)).status_code==401


@pytest.mark.requirement("REQ-CLN-008")
def test_review_package_cli_matches_api_and_never_overwrites_changed_package(workspace,tmp_path):
    target=tmp_path/"review.zip"
    command=[sys.executable,"-m","denguepharma_analytics.cli","--data-dir",str(tmp_path),"clinical-review-package","--workspace",workspace.key,"--output",str(target)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert target.read_bytes()==package(workspace,R1) and events(workspace)==[]
    import_csv(workspace,content([complete(template(workspace)[0])]),R1)
    before=target.read_bytes();result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and "USE_NEW_OUTPUT" in result.stderr and target.read_bytes()==before
