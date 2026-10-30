"""Conector ChEMBL REST API para bioatividades e alvos virais de dengue (REQ-IDN-002, OE1).

Consulta compostos, bioatividades (IC50, EC50, Ki) e alvos moleculares de Flavivírus / DENV 1-4.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

LOG = logging.getLogger("denguepharma.chembl")

DEFAULT_CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


class ChEMBLClient:
    """Cliente HTTP para a API REST pública do ChEMBL."""

    def __init__(self, base_url: str = DEFAULT_CHEMBL_BASE_URL, timeout: int = 15, urlopener=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.urlopener = urlopener or urlopen

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url += "?" + urlencode(filtered_params)

        req = Request(url, headers={"Accept": "application/json", "User-Agent": "DenguePharma-Research/1.0"})
        try:
            with self.urlopener(req, timeout=self.timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))
        except HTTPError as err:
            if err.code == 404:
                return None
            LOG.warning("Erro HTTP %s ao consultar ChEMBL em %s: %s", err.code, url, err.reason)
            raise
        except (URLError, TimeoutError, ValueError) as err:
            LOG.warning("Falha de rede/formato ao consultar ChEMBL em %s: %s", url, err)
            raise

    def lookup_compound(self, query: str) -> dict[str, Any] | None:
        """Busca molécula por ChEMBL ID (ex: CHEMBL1200) ou nome preferido (pref_name)."""
        clean_query = query.strip()
        if not clean_query:
            return None

        # Se for um ChEMBL ID direto
        if clean_query.upper().startswith("CHEMBL"):
            data = self._get_json(f"molecule/{clean_query.upper()}.json")
            if data:
                return self._format_molecule(data)

        # Busca por pref_name case-insensitive
        data = self._get_json("molecule.json", {"pref_name__iexact": clean_query, "limit": 1})
        molecules = data.get("molecules", []) if data else []
        if molecules:
            return self._format_molecule(molecules[0])

        return None

    def search_dengue_targets(self, limit: int = 20) -> list[dict[str, Any]]:
        """Busca alvos moleculares relacionados ao vírus da dengue no ChEMBL."""
        data = self._get_json("target.json", {
            "organism__icontains": "Dengue virus",
            "limit": limit
        })
        targets = data.get("targets", []) if data else []
        return [
            {
                "target_chembl_id": t.get("target_chembl_id"),
                "pref_name": t.get("pref_name"),
                "target_type": t.get("target_type"),
                "organism": t.get("organism"),
                "tax_id": t.get("tax_id"),
            }
            for t in targets
            if t.get("target_chembl_id")
        ]

    def get_compound_activities(self, molecule_chembl_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Recupera bioatividades registradas para uma molécula específica."""
        data = self._get_json("activity.json", {
            "molecule_chembl_id": molecule_chembl_id.upper(),
            "limit": limit
        })
        activities = data.get("activities", []) if data else []
        return [self.normalize_activity(a) for a in activities if a.get("activity_id")]

    def get_target_activities(self, target_chembl_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Recupera bioatividades registradas para um alvo molecular específico."""
        data = self._get_json("activity.json", {
            "target_chembl_id": target_chembl_id.upper(),
            "limit": limit
        })
        activities = data.get("activities", []) if data else []
        return [self.normalize_activity(a) for a in activities if a.get("activity_id")]

    @staticmethod
    def normalize_activity(raw: dict[str, Any]) -> dict[str, Any]:
        """Normaliza um registro bruto de bioatividade do ChEMBL."""
        return {
            "activity_id": raw.get("activity_id"),
            "molecule_chembl_id": raw.get("molecule_chembl_id"),
            "target_chembl_id": raw.get("target_chembl_id"),
            "target_pref_name": raw.get("target_pref_name"),
            "standard_type": raw.get("standard_type"),
            "standard_relation": raw.get("standard_relation"),
            "standard_value": raw.get("standard_value"),
            "standard_units": raw.get("standard_units"),
            "pchembl_value": raw.get("pchembl_value"),
            "assay_type": raw.get("assay_type"),
            "assay_description": raw.get("assay_description"),
        }

    @staticmethod
    def _format_molecule(mol: dict[str, Any]) -> dict[str, Any]:
        props = mol.get("molecule_properties") or {}
        struct = mol.get("molecule_structures") or {}
        return {
            "molecule_chembl_id": mol.get("molecule_chembl_id"),
            "pref_name": mol.get("pref_name"),
            "molecule_type": mol.get("molecule_type"),
            "max_phase": mol.get("max_phase"),
            "oral": mol.get("oral"),
            "canonical_smiles": struct.get("canonical_smiles"),
            "standard_inchi_key": struct.get("standard_inchi_key"),
            "molecular_weight": props.get("full_mwt"),
            "alogp": props.get("alogp"),
        }

