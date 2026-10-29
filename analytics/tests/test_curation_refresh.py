from types import SimpleNamespace

import pytest
from denguepharma_analytics.clinical import refresh


@pytest.mark.requirement('REQ-MIG-006','REQ-CLN-008')
@pytest.mark.parametrize('context,expected', [
    (None,'app'),
    (SimpleNamespace(fragment_ids_this_run=[]),'app'),
    (SimpleNamespace(fragment_ids_this_run=['current-curation']),'fragment'),
])
def test_curation_refresh_uses_legal_runtime_scope(monkeypatch,context,expected):
    requests=[]
    monkeypatch.setattr(refresh,'get_script_run_ctx',lambda **kwargs:context)
    monkeypatch.setattr(refresh.st,'rerun',lambda **kwargs:requests.append(kwargs))
    refresh.rerun_curation()
    assert requests==[{'scope':expected}]


@pytest.mark.requirement('REQ-MIG-006','REQ-CLN-008')
def test_curation_fragment_login_logout_uses_current_session_without_cache(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    def private(path,**kwargs):
        if path=='/login':return {'token':'synthetic-session-'+kwargs['data']['email']}
        assert path=='/workspaces'
        calls.append(kwargs['token'])
        return []
    monkeypatch.setattr(client,'private',private)
    script='from denguepharma_analytics.clinical.ui import curation\ncuration()'
    app=AppTest.from_string(script).run()
    for email in ['first-synthetic-reviewer','second-synthetic-reviewer']:
        next(w for w in app.text_input if w.label=='E-mail').set_value(email)
        next(w for w in app.text_input if w.label=='Senha').set_value('synthetic-test-secret')
        next(w for w in app.button if w.label=='Entrar na curadoria').click().run()
        assert not app.exception
        assert app.session_state['clinical_token']=='synthetic-session-'+email
        assert calls[-1]=='synthetic-session-'+email
        next(w for w in app.button if w.label=='Sair da curadoria').click().run()
        assert not app.exception and 'clinical_token' not in app.session_state
    assert set(calls)=={'synthetic-session-first-synthetic-reviewer','synthetic-session-second-synthetic-reviewer'}


@pytest.mark.requirement('REQ-MIG-006','REQ-CLN-008')
def test_curation_fragment_refresh_never_duplicates_confirmed_action():
    from streamlit.testing.v1 import AppTest
    # A synthetic local counter stands for a successfully confirmed write.
    # A fragment refresh must redraw it without submitting the form again.
    script='''
import streamlit as st
from denguepharma_analytics.clinical.refresh import rerun_curation
if 'confirmed_actions' not in st.session_state: st.session_state.confirmed_actions=0
@st.fragment
def form():
    st.write('Confirmed actions:', st.session_state.confirmed_actions)
    with st.form('synthetic-confirmation'):
        confirmed=st.checkbox('Human confirmation')
        if st.form_submit_button('Confirm synthetic action') and confirmed:
            st.session_state.confirmed_actions+=1
            rerun_curation()
form()
'''
    app=AppTest.from_string(script).run()
    assert not app.exception and app.session_state['confirmed_actions']==0
    app.checkbox[0].check()
    app.button[0].click().run()
    assert not app.exception and app.session_state['confirmed_actions']==1
    app.run()
    assert not app.exception and app.session_state['confirmed_actions']==1
