import json
from io import BytesIO
from urllib.parse import parse_qs,urlsplit

import pytest
from fastapi.testclient import TestClient
from test_review_workflow import workspace,template,complete,content,events,R1,R2,ADMIN
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.review import preview_csv,import_csv,progress


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_rolls_back_events_and_is_reproducible(workspace,monkeypatch):
    data=content([complete(r) for r in template(workspace)])
    before=workspace.snapshot().input_hash
    with monkeypatch.context() as patch:
        patch.setattr(workspace,'append',lambda *args:pytest.fail('Preview must never append events'))
        first=preview_csv(workspace,data,R1)
        assert first==preview_csv(workspace,data,R1)
    assert first['would_import']==first['would_create']==2 and first['would_update']==0
    assert events(workspace)==[] and workspace.snapshot().input_hash==before
    with workspace.transaction() as db:
        assert db.execute("SELECT seq FROM sqlite_sequence WHERE name='events'").fetchone() is None
    assert 'event_ids' not in first and R2.id not in json.dumps(first)
    assert progress(workspace,R1)['missing_independent_votes']==4


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_distinguishes_changes_and_confirmed_import(workspace):
    rows=template(workspace);initial=content([complete(rows[0])])
    import_csv(workspace,initial,R1)
    updated=content([complete(rows[0],decision='INCERTO'),complete(rows[1])])
    before=events(workspace);preview=preview_csv(workspace,updated,R1)
    assert preview['would_update']==preview['would_create']==1 and events(workspace)==before
    assert [r['operation'] for r in preview['changes']]==['UPDATE','CREATE']
    assert import_csv(workspace,updated,R1,expected_preview=preview['receipt'])['imported']==2
    identical=preview_csv(workspace,updated,R1)
    assert identical['unchanged']==2 and identical['would_import']==0
    assert import_csv(workspace,updated,R1,expected_preview=identical['receipt'])['unchanged']==2
    assert len(events(workspace))==3 and not progress(workspace,R1)['calibration_approved']
    assert preview_csv(workspace,content([complete(rows[0],decision='INCERTO'),rows[1]]),R1)['skipped']==1


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_rejects_invalid_late_rows_and_third_reviewer(workspace):
    rows=template(workspace)
    with pytest.raises(ValueError,match='STALE'):
        preview_csv(workspace,content([complete(rows[0]),dict(complete(rows[1]),basis_hash='f'*64)]),R1)
    assert events(workspace)==[]
    data=content([complete(rows[0])]);import_csv(workspace,data,R1);import_csv(workspace,data,R2)
    before=events(workspace)
    with pytest.raises(ValueError,match='TWO_REVIEWERS'):
        preview_csv(workspace,content([complete(rows[1]),complete(rows[0])]),ADMIN)
    assert events(workspace)==before
    with pytest.raises(ValueError,match='NO_COMPLETED'):preview_csv(workspace,content(rows),R1)
    with pytest.raises(ValueError,match='TOO_LARGE'):preview_csv(workspace,b'x'*(1024*1024+1),R1)


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_receipt_binds_actor_file_roles_and_audit(workspace):
    rows=template(workspace);data=content([complete(rows[0])]);receipt=preview_csv(workspace,data,R1)['receipt']
    attempts=[(data,R2),(data,Principal(R1.id,('ADMINISTRADOR',))),
        (content([complete(rows[0],reason='Changed independent review reason')]),R1)]
    for candidate,actor in attempts:
        with pytest.raises(ValueError,match='STALE_REVIEW_PREVIEW'):import_csv(workspace,candidate,actor,expected_preview=receipt)
    assert events(workspace)==[]
    import_csv(workspace,content([complete(rows[1])]),R2)
    before=events(workspace)
    with pytest.raises(ValueError,match='STALE_REVIEW_PREVIEW'):import_csv(workspace,data,R1,expected_preview=receipt)
    assert events(workspace)==before


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_source_change_invalidates_receipt_without_event(workspace):
    rows=template(workspace);data=content([complete(rows[0])]);receipt=preview_csv(workspace,data,R1)['receipt']
    # A source for another study changes, without any audit event.
    document=next(d for d in workspace.input.data['documents'] if d['documentId']=='t1')
    workspace.attach_source(document,'Changed permitted source representation')
    assert events(workspace)==[]
    with pytest.raises(ValueError,match='STALE_REVIEW_PREVIEW'):import_csv(workspace,data,R1,expected_preview=receipt)
    assert preview_csv(workspace,data,R1)['receipt']!=receipt and events(workspace)==[]


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_api_permissions_stale_confirmation_and_no_foreign_votes(workspace,tmp_path):
    actors={'one':R1,'two':R2,'reader':Principal('reader',('LEITOR',))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token]))
    prefix=f'/api/clinical/{workspace.key}/screening';data=content([complete(template(workspace)[0])])
    headers={'Authorization':'Bearer one','Content-Type':'text/csv'}
    assert app.post(prefix+'/preview',content=data).status_code==401
    assert app.post(prefix+'/preview',headers={**headers,'Authorization':'Bearer reader'},content=data).status_code==403
    result=app.post(prefix+'/preview',headers=headers,content=data)
    assert result.status_code==200 and events(workspace)==[]
    receipt=result.json()['receipt']
    assert app.post(prefix+'/import?expected_preview='+receipt,headers={**headers,'Authorization':'Bearer two'},content=data).status_code==409
    assert app.post(prefix+'/import?expected_preview='+receipt,headers=headers,content=data).json()['imported']==1
    assert app.post(prefix+'/import?expected_preview='+receipt,headers=headers,content=data).status_code==409
    second=app.post(prefix+'/preview',headers={**headers,'Authorization':'Bearer two'},content=data).json()
    assert R1.id not in json.dumps(second) and 'votes' not in second
    assert len(events(workspace))==1


def interface(workspace,monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    upload=[content([complete(template(workspace)[0])])];calls=[]
    monkeypatch.setattr(st,'file_uploader',lambda *args,**kwargs:BytesIO(upload[0]))
    def private(path,**kwargs):
        calls.append(path)
        if path.endswith('/preview'):return preview_csv(workspace,kwargs['raw'],R1)
        receipt=parse_qs(urlsplit(path).query)['expected_preview'][0]
        return import_csv(workspace,kwargs['raw'],R1,expected_preview=receipt)
    monkeypatch.setattr(client,'private',private)
    app=AppTest.from_string("from denguepharma_analytics.clinical.review_ui import import_form\nimport_form('workspace','token')",default_timeout=30).run()
    return app,calls,upload


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_form_requires_preview_and_explicit_confirmation(workspace,monkeypatch):
    app,calls,_=interface(workspace,monkeypatch)
    assert not app.exception and len(app.button)==1 and not calls
    app.button[0].click().run()
    assert not app.exception and len(app.button)==2 and calls==['/workspace/screening/preview']
    assert events(workspace)==[]
    app.button[1].click().run()
    assert app.error and len(calls)==1 and events(workspace)==[]
    app.checkbox[0].check();app.button[1].click().run()
    assert not app.exception and app.success and len(events(workspace))==1
    assert len([p for p in calls if '/import?' in p])==1


@pytest.mark.requirement("REQ-CLN-012")
def test_csv_preview_form_discards_changed_upload(workspace,monkeypatch):
    app,calls,upload=interface(workspace,monkeypatch)
    app.button[0].click().run();assert len(app.button)==2
    upload[0]=content([complete(template(workspace)[0],reason='Another independently checked statement')])
    app.run()
    assert not app.exception and app.warning and len(app.button)==1
    assert calls==['/workspace/screening/preview'] and events(workspace)==[]
