"""Convencoes compartilhadas; nenhuma ausencia e completada por inferencia."""
from __future__ import annotations

import hashlib
import json

FIELDS = ["substance", "design", "phase", "serotype", "outcome_category"]
STATES = ["PRESENTE", "NAO_INFORMADO", "NAO_APLICAVEL", "NAO_EXTRAIDO", "INCERTO", "NAO_HOUVE_EVENTO", "SEM_REVISAO", "CONFLITO"]
CONTEXTS = ["HUMANO", "DESAFIO_CONTROLADO", "IN_SILICO", "IN_VITRO", "ANIMAL", "NAO_CLASSIFICADO"]
OUTCOMES = ["CLINICO", "VIROLOGICO", "SEGURANCA", "OUTRO"]
DICTIONARY_VERSION = "descriptive-v2.0"
SCRIPT_VERSION = "analytics-foundation-0.1.0"
NOTICE = "Analise descritiva do corpus filtrado. Zero registros nao comprova ausencia de evidencia na literatura. Rastreabilidade estrutural nao comprova suporte semantico. Nao estima eficacia nem recomenda medicamentos."
CORPUS_NOTICE = ("Panorama descritivo de registros coletados: a elegibilidade pode estar pendente. "
                 "Evidencias revisadas sao apresentadas separadamente. Frequencia nao mede eficacia; "
                 "completude nao mede risco de vies. Zero registros nao demonstra ausencia na literatura.")
MISSING = "[NAO_INFORMADO]"


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def layer(context):
    if context in {"IN_SILICO", "IN_VITRO", "ANIMAL"}: return "PRE_CLINICO"
    if context in {"HUMANO", "DESAFIO_CONTROLADO"}: return "CLINICO"
    return "NAO_CLASSIFICADO"
