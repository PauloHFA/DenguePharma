"""Unidades de registros: NCT valido, ou ID documental; sem identidade clinica inferida."""
from collections import defaultdict
import re

UNIT="registro_consolidado_por_NCT_ou_documento"


def groups(snapshot,*,error_prefix="REGISTRY"):
    result=defaultdict(list);identities={}
    for doc in snapshot.get("documents",[]):
        if doc.get("documentType")!="REGISTRO_ENSAIO":continue
        section=doc.get("metadata",{}).get("protocolSection",{})
        if not isinstance(section,dict):raise ValueError(error_prefix+"_METADATA_INVALID")
        identification=section.get("identificationModule",{})
        if not isinstance(identification,dict):raise ValueError(error_prefix+"_METADATA_INVALID")
        raw=identification.get("nctId")
        nct=raw.strip().upper() if isinstance(raw,str) and re.fullmatch(r"NCT\d{8}",raw.strip(),re.I) else None
        identity=nct or "DOCUMENT:"+doc["documentId"]
        if doc["documentId"] in identities and identities[doc["documentId"]]!=identity:raise ValueError("CONFLICTING_"+error_prefix+"_DOCUMENT_IDENTITY")
        identities[doc["documentId"]]=identity
        missing=raw is None or isinstance(raw,str) and not raw.strip()
        result[identity].append((doc,nct,"PRESENTE" if nct else "NAO_INFORMADO" if missing else "INVALIDO"))
    return result
