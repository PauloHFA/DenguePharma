import copy
import csv
import hashlib
import io
import json
import zipfile

import pytest

from denguepharma_workers.analysis import bundle as shared_bundle
from denguepharma_workers.corpus import analyze, bundle, prepare
from denguepharma_workers.research import validate_pilot


def publication(key="p1", source="PUBMED", **metadata):
    return {"documentId": key, "documentType": "PUBLICACAO", "title": "Documento <script>", "versionId": "v-"+key,
            "source": source, "contentHash": "a"*64, "metadata": {"pmid": "123", "doi": "10.1000/AbC", "pub_year": "2020", **metadata},
            "studyLinks": [{"study_id": "s1", "link_certainty": "CONFIRMADO", "screening_status": "PENDENTE", "context": "NAO_CLASSIFICADO"}]}


def trial(key="t1", actual=False, count=40, countries=None):
    return {"documentId": key, "documentType": "REGISTRO_ENSAIO", "title": "Ensaio", "versionId": "v-"+key, "source": "CLINICALTRIALS", "contentHash": "b"*64,
            "studyLinks": [{"study_id": "s1", "link_certainty": "CONFIRMADO", "screening_status": "PENDENTE", "context": "NAO_CLASSIFICADO"}],
            "metadata": {"hasResults": False, "protocolSection": {"identificationModule": {"nctId": "NCT00000001" if key == "t1" else "NCT00000002"},
                "statusModule": {"startDateStruct": {"date": "2018-02"}, "overallStatus": "COMPLETED"},
                "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"], "enrollmentInfo": {"count": count, "type": "ACTUAL" if actual else "ESTIMATED"}},
                "contactsLocationsModule": {"locations": [{"country": c} for c in (countries or ["Brazil", "Brazil", "France"])]},
                "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "  Drug A "}, {"type": "DRUG", "name": "drug a"}]},
                "referencesModule": {"references": [{"pmid": "123", "type": "RESULT"}]}}}}


def snapshot(documents):
    return {"schemaVersion": "3.0", "dictionaryVersion": "corpus-v3.0", "documents": documents, "studies": [],
            "protocol": {"id": "protocol", "maxRecordsPerSource": 25}}


def content(documents):
    return json.dumps(snapshot(documents)).encode()


def test_contagens_deduplicacao_documental_e_eventos_temporais():
    summary, records = analyze(content([publication(), publication("p2", "EUROPE_PMC", doi="https://doi.org/10.1000/abc"), trial()]))
    assert summary["rawDocumentCount"] == 3 and summary["documentCount"] == 2
    assert summary["publicationCount"] == 1 and summary["trialCount"] == 1
    assert summary["distinctConfirmedStudyCount"] == 1
    assert {(r["field"], r["category"]) for r in summary["temporal"]} == {("publication_year", "2020"), ("start_year", "2018")}
    assert summary["studyCount"] == 0  # Nunca promover metadados a evidencia revisada.
    assert records[0]["context"] == "NAO_CLASSIFICADO"


def test_multiplos_paises_intervencoes_e_denominadores():
    summary, _ = analyze(content([trial(), trial("t2", countries=["Brazil"])]))
    countries = {r["category"]: r for r in summary["distributions"] if r["field"] == "countries"}
    assert countries["Brazil"]["count"] == 2
    assert countries["France"]["proportion"] == .5
    assert sum(r["proportion"] for r in countries.values()) == 1.5
    substance = next(r for r in summary["distributions"] if r["field"] == "substances")
    assert substance["count"] == 2 and substance["category"] == "drug a"


def test_inscricao_efetiva_prevista_zero_e_booleano():
    invalid = trial("t3", count=True)
    summary, _ = analyze(content([trial(count=0), trial("t2", actual=True, count=10), invalid]))
    enrollment = {r["field"]: r for r in summary["enrollment"]}
    assert enrollment["enrollment_estimated"]["median"] == 0
    assert enrollment["enrollment_actual"]["median"] == 10
    assert enrollment["enrollment_estimated"]["available"] == 1
    assert enrollment["enrollment_estimated"]["denominator"] == 2  # t2/t3 same NCT: conflito, nao dupla contagem.
    has_results = next(r for r in summary["completeness"] if r["field"] == "has_results")
    assert has_results["present"] == 2  # False e um valor informado.


def test_valores_divergentes_nao_escolhem_fonte_e_vinculos_ambiguos():
    duplicate = publication("p2", "EUROPE_PMC", pub_year="2021")
    duplicate["studyLinks"][0]["study_id"] = "another"
    summary, records = analyze(content([publication(), duplicate]))
    assert records[0]["publication_year"] is None
    assert records[0]["study_id"] is None
    assert summary["conflicts"][0]["field"] == "publication_year"
    row = next(r for r in summary["completeness"] if r["source"] == "PUBMED" and r["field"] == "publication_year")
    assert row["present"] == 0 and row["conflicts"] == 1


def test_referencias_sao_candidatas_e_apenas_curadoria_confirma():
    t = trial(); t["studyLinks"][0]["study_id"] = "other"
    summary, _ = analyze(content([publication(), t]))
    assert summary["linkCoverage"]["numerator"] == 0 and len(summary["linkCandidates"]) == 1
    summary, _ = analyze(content([publication(), trial()]))
    assert summary["linkCoverage"]["proportion"] == 1 and len(summary["links"]) == 1
    assert next(r for r in summary["distributions"] if r["field"] == "has_results")["category"] == "False"


def test_vazio_sem_metricas_artificiais_e_pacote_reproduzivel():
    summary, records = analyze(content([]))
    assert summary["status"] == "NO_DATA" and records == []
    assert summary["linkCoverage"]["proportion"] is None
    assert all(r["median"] is None for r in summary["enrollment"])
    files = bundle(content([])); assert b"Sem dados" in files["report.html"]
    assert files == shared_bundle(content([]))
    manifest = json.loads(files["manifest.json"])
    for name, expected in manifest["artifacts"].items(): assert hashlib.sha256(files[name]).hexdigest() == expected
    with zipfile.ZipFile(io.BytesIO(files["bundle.zip"])) as archive: assert "pilot_review.csv" in archive.namelist()


def test_pacote_nao_vazio_tem_graficos_mapa_e_rastreio():
    files = shared_bundle(content([publication(), trial()]))
    assert {"figures/countries_map.png", "figures/enrollment.png", "figures/temporal.png", "figures/completeness.png", "records.json", "documents.csv"} <= files.keys()
    assert b"<script>" not in files["report.html"]
    summary = json.loads(files["summary.json"])
    assert "Brazil" in summary["geography"]["matchedCountries"]
    assert summary["geography"]["unmappedCountries"] == []


def test_comparacao_snapshot_distingue_nao_observado_de_retratado():
    data = snapshot([publication()])
    old = publication(); old["contentHash"] = "c"*64
    data["previous"] = {"analysisId": "old", "protocol": {"id": "different"}, "documents": [old, trial()]}
    summary, _ = analyze(json.dumps(data).encode())
    assert summary["changes"]["changed"] == ["p1"]
    assert summary["changes"]["notObserved"] == ["t1"]
    assert summary["changes"]["comparable"] is False


def test_coleta_completa_exige_revisao_do_piloto_correspondente(tmp_path):
    dataset = tmp_path / "dataset.json"; dataset.write_bytes(content([publication()]))
    review = tmp_path / "review.csv"; review.write_bytes(bundle(dataset.read_bytes())["pilot_review.csv"])
    with pytest.raises(ValueError, match="pendente"): validate_pilot(review, dataset)
    rows = list(csv.DictReader(io.StringIO(review.read_text(encoding="utf-8"))))
    rows[0].update(preparation_validated="SIM", eligibility_decision="INCLUIR", reviewer="Pessoa", reviewed_at="2026-10-27")
    with review.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    assert validate_pilot(review, dataset)["reviewedRecords"] == 1
    rows[0]["document_id"] = "outro"
    with review.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(ValueError, match="corresponder"): validate_pilot(review, dataset)


def test_documento_duplicado_com_versoes_divergentes_falha():
    doc = publication(); duplicate = copy.deepcopy(doc); duplicate["contentHash"] = "c"*64
    with pytest.raises(ValueError, match="VERSION_CONFLICT"): prepare(snapshot([doc, duplicate]))


def test_fase_nao_aplicavel_nao_vira_campo_preenchido():
    doc = trial(); doc["metadata"]["protocolSection"]["designModule"]["phases"] = ["NA"]
    summary, _ = analyze(content([doc]))
    row = next(r for r in summary["completeness"] if r["field"] == "phases")
    assert row["present"] == 0 and row["not_applicable"] == 1 and row["applicable"] == 0
    assert row["proportion"] is None


def test_identidade_pubchem_somente_quando_alias_exato_e_nao_ambiguo():
    source = snapshot([trial()])
    source["chemicalMappings"] = [{"pubchem_cid": "123", "published_name": "drug a", "normalized_name": "Compound A", "alias": "drug a"}]
    records, _, _ = prepare(source)
    assert records[0]["substances"] == ["Compound A"]
    assert records[0]["chemical_entities"][0]["pubchem_cid"] == "123"
    source["chemicalMappings"].append({"pubchem_cid": "456", "published_name": "drug a"})
    records, _, _ = prepare(source)
    assert records[0]["substances"] == ["drug a"]
    assert records[0]["chemical_entities"][0]["identity_status"] == "AMBIGUO"


def test_disponibilidade_cientifica_conta_estudos_e_preserva_conflitos():
    source = snapshot([])
    source["studies"] = [{"studyId": key, "context": "HUMANO", "purpose": "TRATAMENTO", "fields": {}} for key in ("a", "b", "c")]
    source["scientificFields"] = [
        {"study_id": "a", "field_name": "population", "status": "PRESENTE", "value": "Adultos"},
        {"study_id": "a", "field_name": "population", "status": "PRESENTE", "value": "Adultos"},
        {"study_id": "b", "field_name": "population", "status": "PRESENTE", "value": "Adultos"},
        {"study_id": "b", "field_name": "population", "status": "PRESENTE", "value": "Criancas"},
        {"study_id": "c", "field_name": "comparator", "status": "NAO_APLICAVEL", "value": None},
    ]
    summary, _ = analyze(json.dumps(source).encode())
    population = next(r for r in summary["scientificFieldAvailability"] if r["field"] == "population")
    assert population["present"] == 1 and population["applicable"] == 3
    assert population["states"] == {"PRESENTE": 1, "CONFLITO": 1, "SEM_REVISAO": 1}
    comparator = next(r for r in summary["scientificFieldAvailability"] if r["field"] == "comparator")
    assert comparator["applicable"] == 2


def test_ano_apos_corte_e_sinalizado_sem_correcao_inventada():
    source = snapshot([publication(pub_year="2027")])
    source["protocol"]["cutoff_date"] = "2026-10-27"
    summary, records = analyze(json.dumps(source).encode())
    assert records[0]["publication_year"] == 2027
    assert summary["temporalFlags"][0]["document_id"] == "p1"
