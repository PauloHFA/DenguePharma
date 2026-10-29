import hashlib
import json
from pathlib import Path
import sys

import pytest
from denguepharma_analytics.sources.snapshot import load_snapshot


@pytest.fixture(autouse=True)
def requirement_properties(request):
    marker = request.node.get_closest_marker("requirement")
    if marker: request.node.user_properties.append(("requirements", ",".join(marker.args)))


@pytest.fixture
def snapshot():
    def publication(key, source="PUBMED"):
        return {"documentId": key, "versionId": "v-"+key, "version": 1, "documentType": "PUBLICACAO", "title": "Artigo <script>texto</script>",
            "source": source, "contentHash": hashlib.sha256(key.encode()).hexdigest(), "license": "NAO_VERIFICADA", "accessStatus": "SOMENTE_RESUMO",
            "retrievedAt": "2026-10-27T12:00:00Z", "metadata": {"pmid": "123", "doi": "10.1000/abc", "pub_year": "2027", "abstract": "PRIVATE_FULLTEXT", "contacts": "PRIVATE_CONTACT"},
            "studyLinks": [{"study_id": "s1", "link_certainty": "CONFIRMADO", "screening_status": "AGUARDANDO_TITULO_RESUMO", "context": "NAO_CLASSIFICADO", "purpose": None}]}
    trial = {"documentId": "t1", "versionId": "v-t1", "version": 1, "documentType": "REGISTRO_ENSAIO", "title": "Ensaio",
        "source": "CLINICALTRIALS", "contentHash": "b"*64, "studyLinks": [{"study_id": "s2", "link_certainty": "CONFIRMADO", "screening_status": "AGUARDANDO_TITULO_RESUMO", "context": "NAO_CLASSIFICADO"}],
        "metadata": {"hasResults": False, "protocolSection": {"identificationModule": {"nctId": "NCT00000001"},
            "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2020-01"}},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"], "enrollmentInfo": {"count": 0, "type": "ACTUAL"}},
            "contactsLocationsModule": {"locations": [{"country": "Brazil"}, {"country": "France"}, {"country": "Brazil"}]},
            "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Drug A"}, {"type": "DRUG", "name": "drug a"}]}}}}
    data = {"schemaVersion": "3.0", "dictionaryVersion": "corpus-v3.0", "snapshotId": "test-snapshot", "createdAt": "2026-10-27T12:00:00Z",
        "documents": [publication("p1"), publication("p2", "EUROPE_PMC"), trial], "studies": [], "scientificFields": [],
        "protocol": {"id": "protocol", "code": "TEST-PILOT", "version": 1, "cutoff_date": "2026-10-27", "maxRecordsPerSource": 25},
        "sourceRuns": [{"source": "PUBMED", "status": "COMPLETED", "params": {"api_key": "PRIVATE_KEY"}}]}
    return load_snapshot(json.dumps(data).encode())


@pytest.fixture
def prepared(tmp_path, snapshot):
    from denguepharma_analytics.storage import export, publish
    root = tmp_path / "data"; manifest = export(snapshot, root); publish(root, manifest["run_id"])
    return root, manifest


def legacy_imports():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "workers" / "src"))
    from denguepharma_workers.corpus import prepare, analyze
    return prepare, analyze
