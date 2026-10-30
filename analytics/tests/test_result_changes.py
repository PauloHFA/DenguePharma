import copy
import json

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,include,result,approve
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.extraction import preview
from denguepharma_analytics.clinical.result_changes import compare,differences,view


def history(workspace):
    with workspace.transaction() as db:return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-009')
def test_result_differences_preserve_missing_null_zero_and_escaped_paths():
    rows=differences({'n':None,'events':0,'domains':{}},{'n':0,'domains':{'a/b~c':'checked'}})
    indexed={r['path']:r for r in rows}
    assert indexed['/n']['before'] is None and indexed['/n']['after']==0
    assert indexed['/events']['before']==0 and not indexed['/events']['after_exists']
    assert indexed['/domains/a~1b~0c']['after']=='checked' and not indexed['/domains/a~1b~0c']['before_exists']
    assert differences({'value':True},{'value':1})
    assert not differences({'a':1,'b':2},{'b':2,'a':1})


@pytest.mark.requirement('REQ-CLN-009')
def test_result_reference_changes_are_order_independent_and_do_not_return_quotes(workspace):
    include(workspace);before=result(workspace);after=copy.deepcopy(before)
    after['evidence'].reverse()
    assert compare(before,after)['references_changed'] is False
    after['evidence'][0]['quote']='Synthetic private replacement excerpt'
    report=compare(before,after)
    assert report['references_changed'] and not report['field_changes']
    assert 'Synthetic private replacement excerpt' not in json.dumps(report)
    assert before['evidence'][0]['quote'] not in json.dumps(report)
    assert all('quote' not in r and 'quote_hash' in r for r in report['references_after'])


@pytest.mark.requirement('REQ-CLN-009')
def test_result_correction_preview_matches_saved_changes_without_approving(workspace):
    include(workspace);payload=result(workspace);prior=approve(workspace,payload)
    correction=copy.deepcopy(payload);correction.update(supersedes=prior,correction_reason='Synthetic corrected event count')
    correction['treatment']['events']=5
    before=history(workspace);snapshot=workspace.snapshot().input_hash
    checked=preview(workspace,correction,R1)
    change=next(c for c in checked['changes']['field_changes'] if c['path']=='/treatment/events')
    assert change['before']==10 and change['after']==5
    assert checked['support']['complete'] and checked['published'] is False
    assert history(workspace)==before and workspace.snapshot().input_hash==snapshot
    current=workspace.act('RESULT_DRAFTED',correction,R1)['event_id']
    saved=view(workspace,current,R2)
    assert saved['predecessor_id']==prior and saved['current_basis'] and saved['kind']=='CORRECAO'
    assert saved['field_changes']==checked['changes']['field_changes']
    assert workspace.freeze()['results'][0]['result_id']==prior
    approve(workspace,correction)
    assert workspace.freeze()['results'][0]['treatment']['events']==5


@pytest.mark.requirement('REQ-CLN-009')
def test_result_reference_diff_does_not_validate_literal_support(workspace):
    include(workspace);payload=result(workspace)
    prior=workspace.act('RESULT_DRAFTED',payload,R1)['event_id']
    correction=copy.deepcopy(payload);correction.update(supersedes=prior,correction_reason='Synthetic source reference correction')
    correction['evidence'][0]['quote']='Synthetic unsupported private quotation'
    checked=preview(workspace,correction,R1)
    assert not checked['support']['complete']
    assert checked['changes']['references_changed'] and not checked['changes']['field_changes']
    assert 'Synthetic unsupported private quotation' not in json.dumps(checked['changes'])
    assert len(history(workspace))==3 and not workspace.freeze()['results']


@pytest.mark.requirement('REQ-CLN-009')
def test_result_changes_api_is_private_readonly_and_handles_initial_result(workspace,tmp_path):
    include(workspace);payload=result(workspace)
    prior=workspace.act('RESULT_DRAFTED',payload,R1)['event_id']
    initial=view(workspace,prior,R1)
    assert initial['kind']=='RESULTADO_INICIAL' and not initial['field_changes']
    correction={**payload,'supersedes':prior,'correction_reason':'Synthetic checked correction'}
    current=workspace.act('RESULT_DRAFTED',correction,R1)['event_id']
    before=history(workspace)
    app=TestClient(create_app(tmp_path,authenticate=lambda token:R2 if token=='reviewer' else Principal('reader',('LEITOR',))))
    url=f'/api/clinical/{workspace.key}/results/{current}/changes'
    assert app.get(url).status_code==401
    assert app.get(url,headers={'Authorization':'Bearer reader'}).status_code==403
    headers={'Authorization':'Bearer reviewer'}
    response=app.get(url,headers=headers)
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    assert response.json()==view(workspace,current,R2)
    assert app.get(url.replace(current,'missing'),headers=headers).status_code==404
    assert R1.id not in response.text and R2.id not in response.text
    assert history(workspace)==before


@pytest.mark.requirement('REQ-CLN-009')
def test_result_changes_remain_inspectable_when_sources_are_stale(workspace):
    include(workspace);payload=result(workspace)
    prior=workspace.act('RESULT_DRAFTED',payload,R1)['event_id']
    correction={**payload,'supersedes':prior,'correction_reason':'Synthetic old correction'}
    current=workspace.act('RESULT_DRAFTED',correction,R1)['event_id']
    workspace.attach_source(workspace.input.data['documents'][0],'Synthetic updated normalized source')
    report=view(workspace,current,R2)
    assert not report['current_basis'] and report['predecessor_id']==prior
    assert not workspace.freeze()['results']


@pytest.mark.requirement('REQ-CLN-009')
def test_result_changes_ui_preserves_mixed_value_types_without_writing():
    from streamlit.testing.v1 import AppTest
    data=compare({'n':None,'events':0},{'n':0,'reason':'Synthetic added text'})
    script='from denguepharma_analytics.clinical.result_changes_ui import render\nrender('+repr(data)+')'
    app=AppTest.from_string(script).run()
    assert not app.exception and not app.button
    frame=app.dataframe[0].value
    assert 'CAMPO_AUSENTE' in list(frame['depois'])
    assert 'null' in list(frame['antes']) and '0' in list(frame['depois'])
