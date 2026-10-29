import copy
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace, R1, R2, ADJ, screen
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.dossier import view
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.workspace import create
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


def audit(workspace):
    with workspace.transaction() as db:
        return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-008')
def test_dossier_is_blind_readonly_and_scoped_to_current_study(workspace):
    screen(workspace, R2)
    before = audit(workspace)
    frozen = workspace.snapshot().input_hash
    dossier = view(workspace, 's1', R1)
    assert [d['document_id'] for d in dossier['documents']] == ['p1', 'p2']
    assert all(v['document_id'] == d['document_id'] for d in dossier['documents'] for v in d['source_versions'])
    assert dossier['documents'][0]['identifiers'] == {'pmid': '123', 'doi': '10.1000/abc'}
    assert dossier['basis_hash'] == next(r for r in workspace.queue(R1) if r['study_id'] == 's1')['basis_hash']
    serialized = json.dumps(dossier)
    for forbidden in [R2.id, 'classification', 'votes', 'own_decision', 'TEST-DRUG', 'PRIVATE_KEY', 'PRIVATE_CONTACT']:
        assert forbidden not in serialized
    assert 'text' not in dossier['documents'][0]['source_versions'][0]
    assert view(workspace, 's1', ADJ) == dossier
    assert audit(workspace) == before and workspace.snapshot().input_hash == frozen
    trial = view(workspace, 's2', R1)
    assert trial['documents'][0]['identifiers']['nct'] == 'NCT00000001'


@pytest.mark.requirement('REQ-CLN-008')
def test_dossier_stale_basis_enrichment_and_identity_change(workspace):
    old = view(workspace, 's1', R1)
    document = workspace.input.data['documents'][0]
    added = workspace.attach_source(document, 'Synthetic new permitted normalized representation')
    with pytest.raises(ValueError, match='STALE_STUDY_BASIS'):
        view(workspace, 's1', R1, expected_basis=old['basis_hash'])
    current = view(workspace, 's1', R1)
    assert len(current['documents']) == 2
    assert added in [v['version_id'] for d in current['documents'] for v in d['source_versions']]
    workspace.act('DOCUMENT_LINKED', dict(document_id='p1', study_id='s2', reason='Synthetic source identity reviewed'), ADJ)
    with pytest.raises(ValueError, match='STALE_STUDY_BASIS'):
        view(workspace, 's1', R1, expected_basis=current['basis_hash'])
    assert [d['document_id'] for d in view(workspace, 's1', R1)['documents']] == ['p2']
    assert [d['document_id'] for d in view(workspace, 's2', R1)['documents']] == ['p1', 't1']


@pytest.mark.requirement('REQ-CLN-008')
def test_dossier_unknown_missing_text_ambiguity_and_permissions(workspace, tmp_path):
    with pytest.raises(ValueError, match='UNKNOWN_STUDY'):
        view(workspace, 'missing', R1)
    with pytest.raises(PermissionError):
        view(workspace, 's1', Principal('reader', ('LEITOR',)))
    data = copy.deepcopy(workspace.input.data)
    data['documents'][0]['studyLinks'].append(dict(study_id='s2', link_certainty='CONFIRMADO'))
    other = create(tmp_path/'ambiguous', load_snapshot(json_bytes(data)), workspace.protocol)
    assert view(other, 'p1', R1)['unresolved_identity_documents'] == ['p1']
    # Simulate an incomplete source import, not a missing scientific value.
    with sqlite3.connect(other.folder/'curation.sqlite3') as db:
        db.execute('DROP TRIGGER sources_no_delete')
        db.execute("DELETE FROM sources WHERE document_id='p1'")
    missing = view(other, 'p1', R1)
    assert missing['documents'][0]['source_versions'] == []


@pytest.mark.requirement('REQ-CLN-008')
@pytest.mark.parametrize('field,value,message', [
    ('text', 'corrupted normalized text', 'SOURCE_TEXT_HASH_MISMATCH'),
    ('content_hash', '0'*64, 'SOURCE_CONTENT_HASH_MISMATCH'),
])
def test_dossier_refuses_corrupted_source_representations(workspace, field, value, message):
    with sqlite3.connect(workspace.folder/'curation.sqlite3') as db:
        db.execute('DROP TRIGGER sources_no_update')
        db.execute(f'UPDATE sources SET {field}=? WHERE document_id=?', (value, 'p1'))
    with pytest.raises(ValueError, match=message):
        view(workspace, 's1', R1)


@pytest.mark.requirement('REQ-CLN-008')
def test_dossier_api_requires_auth_and_never_caches_private_context(workspace, tmp_path):
    app = TestClient(create_app(tmp_path, authenticate=lambda token:
        R1 if token == 'reviewer' else Principal('reader', ('LEITOR',))))
    url = f'/api/clinical/{workspace.key}/studies/s1/dossier'
    assert app.get(url).status_code == 401
    assert app.get(url, headers={'Authorization':'Bearer reader'}).status_code == 403
    headers = {'Authorization':'Bearer reviewer'}
    response = app.get(url, headers=headers)
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    assert response.json() == view(workspace, 's1', R1)
    assert app.get(url, params={'basis_hash':'stale'}, headers=headers).status_code == 409
    assert app.get(url.replace('/s1/', '/missing/'), headers=headers).status_code == 404
    assert audit(workspace) == []
