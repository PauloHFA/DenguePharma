import io
import json
from urllib.error import HTTPError
import pytest
from denguepharma_workers.chembl import ChEMBLClient


class MockResponse:
    def __init__(self, data: dict, status: int = 200):
        self.data = json.dumps(data).encode("utf-8")
        self.status = status

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_lookup_compound_by_chembl_id():
    mock_mol = {
        "molecule_chembl_id": "CHEMBL1200",
        "pref_name": "SOFOSBUVIR",
        "molecule_type": "Small molecule",
        "max_phase": 4,
        "oral": True,
        "molecule_structures": {"canonical_smiles": "CC(C)OC(=O)..."},
        "molecule_properties": {"full_mwt": "529.45", "alogp": "1.62"},
    }

    def opener(req, timeout=15):
        assert "molecule/CHEMBL1200.json" in req.full_url
        return MockResponse(mock_mol)

    client = ChEMBLClient(urlopener=opener)
    result = client.lookup_compound("CHEMBL1200")
    assert result is not None
    assert result["molecule_chembl_id"] == "CHEMBL1200"
    assert result["pref_name"] == "SOFOSBUVIR"
    assert result["molecular_weight"] == "529.45"
    assert result["max_phase"] == 4


def test_lookup_compound_by_name():
    mock_data = {
        "molecules": [
            {
                "molecule_chembl_id": "CHEMBL521",
                "pref_name": "CHLOROQUINE",
                "molecule_type": "Small molecule",
                "max_phase": 4,
                "molecule_structures": {"canonical_smiles": "CCN(CC)CCCC(C)Nc1c2..."},
                "molecule_properties": {"full_mwt": "319.88"},
            }
        ]
    }

    def opener(req, timeout=15):
        assert "pref_name__iexact=chloroquine" in req.full_url.lower()
        return MockResponse(mock_data)

    client = ChEMBLClient(urlopener=opener)
    result = client.lookup_compound("chloroquine")
    assert result is not None
    assert result["molecule_chembl_id"] == "CHEMBL521"
    assert result["pref_name"] == "CHLOROQUINE"


def test_lookup_compound_not_found_returns_none():
    def opener(req, timeout=15):
        raise HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b""))

    client = ChEMBLClient(urlopener=opener)
    assert client.lookup_compound("CHEMBL99999999") is None
    assert client.lookup_compound("") is None


def test_search_dengue_targets():
    mock_targets = {
        "targets": [
            {
                "target_chembl_id": "CHEMBL5980",
                "pref_name": "Serine protease NS3",
                "target_type": "SINGLE PROTEIN",
                "organism": "Dengue virus type 2",
                "tax_id": 11060,
            },
            {
                "target_chembl_id": "CHEMBL613768",
                "pref_name": "RNA-directed RNA polymerase catalytic subunit",
                "target_type": "SINGLE PROTEIN",
                "organism": "Dengue virus type 1",
                "tax_id": 11053,
            },
        ]
    }

    def opener(req, timeout=15):
        assert "organism__icontains=Dengue+virus" in req.full_url or "organism__icontains=Dengue" in req.full_url
        return MockResponse(mock_targets)

    client = ChEMBLClient(urlopener=opener)
    targets = client.search_dengue_targets()
    assert len(targets) == 2
    assert targets[0]["target_chembl_id"] == "CHEMBL5980"
    assert "NS3" in targets[0]["pref_name"]
    assert targets[1]["target_chembl_id"] == "CHEMBL613768"


def test_get_compound_and_target_activities():
    mock_activities = {
        "activities": [
            {
                "activity_id": 123456,
                "molecule_chembl_id": "CHEMBL1200",
                "target_chembl_id": "CHEMBL613768",
                "target_pref_name": "RNA-directed RNA polymerase",
                "standard_type": "IC50",
                "standard_relation": "=",
                "standard_value": "4.2",
                "standard_units": "uM",
                "pchembl_value": "5.38",
                "assay_type": "B",
                "assay_description": "Inhibition of DENV-1 RdRp",
            }
        ]
    }

    def opener(req, timeout=15):
        return MockResponse(mock_activities)

    client = ChEMBLClient(urlopener=opener)
    acts = client.get_compound_activities("CHEMBL1200")
    assert len(acts) == 1
    assert acts[0]["standard_type"] == "IC50"
    assert acts[0]["standard_value"] == "4.2"
    assert acts[0]["standard_units"] == "uM"

    target_acts = client.get_target_activities("CHEMBL613768")
    assert len(target_acts) == 1
    assert target_acts[0]["target_chembl_id"] == "CHEMBL613768"
