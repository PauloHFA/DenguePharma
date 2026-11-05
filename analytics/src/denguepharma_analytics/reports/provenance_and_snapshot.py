"""
Módulo M07: Proveniência de Relatórios e Reprodutibilidade via ReportSnapshot (REQ-REL-001, REQ-REL-002).
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import re
from typing import Any, Dict, List, Literal, Optional, Tuple


class MissingProvenanceError(ValueError):
    """Lançado quando qualquer um dos campos mandatórios de proveniência está ausente ou vazio (REQ-REL-001)."""
    pass


class SnapshotIntegrityError(ValueError):
    """Lançado quando o ReportSnapshot foi violado ou seus dados foram adulterados (REQ-REL-002)."""
    pass


def canonical_json_bytes(obj: Any) -> bytes:
    """Serializa qualquer objeto Python para JSON canônico determinístico bit-a-bit."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_digest(content: bytes) -> str:
    """Calcula hash criptográfico SHA-256."""
    return hashlib.sha256(content).hexdigest()


@dataclass
class ReportProvenance:
    """
    Estrutura mandatória de proveniência de relatórios (REQ-REL-001).
    Todo relatório (PDF, CSV ou JSON) deve incluir:
    - fontes (sources)
    - data de consulta (query_date)
    - versões (versions)
    - filtros (filters)
    - status da evidência (evidence_status)
    - limitações (limitations)
    """
    sources: List[str]
    query_date: str
    versions: Dict[str, str]
    filters: Dict[str, Any]
    evidence_status: str
    limitations: List[str]

    def validate(self) -> None:
        if not self.sources or not any(str(s).strip() for s in self.sources):
            raise MissingProvenanceError("REQ-REL-001: 'sources' é obrigatório e não pode ser vazio.")
        if not self.query_date or not str(self.query_date).strip():
            raise MissingProvenanceError("REQ-REL-001: 'query_date' é obrigatório.")
        if not self.versions or not isinstance(self.versions, dict):
            raise MissingProvenanceError("REQ-REL-001: 'versions' é obrigatório e deve ser um dicionário.")
        if self.filters is None or not isinstance(self.filters, dict):
            raise MissingProvenanceError("REQ-REL-001: 'filters' é obrigatório.")
        if not self.evidence_status or not str(self.evidence_status).strip():
            raise MissingProvenanceError("REQ-REL-001: 'evidence_status' é obrigatório.")
        if not self.limitations or not any(str(lim).strip() for lim in self.limitations):
            raise MissingProvenanceError("REQ-REL-001: 'limitations' é obrigatório e não pode ser vazio.")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReportProvenance:
        prov = cls(
            sources=list(data.get("sources") or []),
            query_date=str(data.get("query_date") or ""),
            versions=dict(data.get("versions") or {}),
            filters=dict(data.get("filters") or {}),
            evidence_status=str(data.get("evidence_status") or ""),
            limitations=list(data.get("limitations") or []),
        )
        prov.validate()
        return prov


@dataclass
class ReportSnapshot:
    """
    Snapshot imutável e determinístico de relatório (REQ-REL-002).
    Permite reproduzir relatórios de forma idêntica mesmo após atualizações nas fontes.
    """
    snapshot_id: str
    created_at: str
    provenance: ReportProvenance
    raw_records: List[Dict[str, Any]]
    source_data_hash: str

    @classmethod
    def create(
        cls,
        snapshot_id: str,
        created_at: str,
        provenance: ReportProvenance,
        raw_records: List[Dict[str, Any]],
    ) -> ReportSnapshot:
        provenance.validate()
        # Ordenação determinística dos registros para reprodutibilidade bit-a-bit
        sorted_records = sorted(raw_records, key=lambda r: json.dumps(r, sort_keys=True))
        data_hash = sha256_digest(canonical_json_bytes(sorted_records))
        return cls(
            snapshot_id=snapshot_id,
            created_at=created_at,
            provenance=provenance,
            raw_records=sorted_records,
            source_data_hash=data_hash,
        )

    def verify_integrity(self) -> None:
        self.provenance.validate()
        recalculated = sha256_digest(canonical_json_bytes(self.raw_records))
        if recalculated != self.source_data_hash:
            raise SnapshotIntegrityError(
                f"REQ-REL-002: Adulteração detectada no snapshot {self.snapshot_id}. "
                f"Hash esperado: {self.source_data_hash}, calculado: {recalculated}"
            )


def _render_deterministic_pdf(
    snapshot: ReportSnapshot,
) -> bytes:
    """Gera um PDF 1.4 puramente determinístico e bit-a-bit reproduzível com os metadados mandatórios."""
    prov = snapshot.provenance
    # Formatação do timestamp para formato de metadado PDF padrão
    clean_date = re.sub(r"[^0-9]", "", snapshot.created_at)[:14].ljust(14, "0")

    lines = [
        "RELATORIO CIENTIFICO DENGUEPHARMA - METADADOS MANDATORIOS",
        f"Snapshot ID: {snapshot.snapshot_id}",
        f"Data da Consulta: {prov.query_date}",
        f"Fontes: {', '.join(prov.sources)}",
        f"Versoes: {json.dumps(prov.versions, sort_keys=True)}",
        f"Filtros: {json.dumps(prov.filters, sort_keys=True)}",
        f"Status da Evidencia: {prov.evidence_status}",
        f"Limitacoes: {'; '.join(prov.limitations)}",
        "------------------------------------------------------------",
        f"Registros Analisados ({len(snapshot.raw_records)} itens):",
    ]
    for idx, rec in enumerate(snapshot.raw_records[:10]):
        summary_str = f"[{idx + 1}] " + ", ".join(f"{k}={v}" for k, v in sorted(rec.items()))
        lines.append(summary_str[:85])
    if len(snapshot.raw_records) > 10:
        lines.append(f"... e mais {len(snapshot.raw_records) - 10} registros.")

    content_stream = "BT /F1 10 Tf 40 780 Td 14 TL\n"
    for line in lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream += f"({safe_line}) ' \n"
    content_stream += "ET"
    stream_bytes = content_stream.encode("latin1", errors="replace")
    stream_len = len(stream_bytes)

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1") + stream_bytes + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"6 0 obj\n<< /CreationDate (D:{clean_date}) /Producer (DenguePharma Deterministic Engine) >>\nendobj\n".encode("latin1"),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode("latin1")
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
    return pdf


def _render_deterministic_csv(snapshot: ReportSnapshot) -> bytes:
    """Gera um CSV determinístico com cabeçalho de proveniência formal (REQ-REL-001)."""
    prov = snapshot.provenance
    output = io.StringIO()
    output.write("# --- DENGUEPHARMA REPORT PROVENANCE BEGIN ---\n")
    output.write(f"# sources: {json.dumps(prov.sources, ensure_ascii=False)}\n")
    output.write(f"# query_date: {prov.query_date}\n")
    output.write(f"# versions: {json.dumps(prov.versions, sort_keys=True, ensure_ascii=False)}\n")
    output.write(f"# filters: {json.dumps(prov.filters, sort_keys=True, ensure_ascii=False)}\n")
    output.write(f"# evidence_status: {prov.evidence_status}\n")
    output.write(f"# limitations: {json.dumps(prov.limitations, ensure_ascii=False)}\n")
    output.write(f"# snapshot_id: {snapshot.snapshot_id}\n")
    output.write("# --- DENGUEPHARMA REPORT PROVENANCE END ---\n")

    if snapshot.raw_records:
        fieldnames = sorted({k for r in snapshot.raw_records for k in r.keys()})
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for rec in snapshot.raw_records:
            writer.writerow(rec)
    return output.getvalue().encode("utf-8")


def _render_deterministic_json(snapshot: ReportSnapshot) -> bytes:
    """Gera um JSON canônico determinístico com seção explícita de proveniência (REQ-REL-001)."""
    payload = {
        "report_snapshot_id": snapshot.snapshot_id,
        "created_at": snapshot.created_at,
        "source_data_hash": snapshot.source_data_hash,
        "provenance": snapshot.provenance.to_dict(),
        "records": snapshot.raw_records,
    }
    return canonical_json_bytes(payload)


def render_report(
    snapshot: ReportSnapshot,
    format: Literal["json", "csv", "pdf"],
) -> bytes:
    """
    Renderiza o relatório no formato especificado de forma 100% determinística.
    Verifica a integridade do snapshot antes da renderização.
    """
    snapshot.verify_integrity()
    fmt = format.lower().strip()
    if fmt == "json":
        return _render_deterministic_json(snapshot)
    elif fmt == "csv":
        return _render_deterministic_csv(snapshot)
    elif fmt == "pdf":
        return _render_deterministic_pdf(snapshot)
    else:
        raise ValueError(f"Formato de relatório não suportado: {format}")


def inspect_report_provenance(
    content: bytes,
    format: Literal["json", "csv", "pdf"],
) -> Dict[str, Any]:
    """
    Inspeciona um relatório nos formatos JSON, CSV ou PDF e valida a presença
    de todos os 6 itens mandatórios de proveniência (ACC-REL-001):
    fontes, data de consulta, versões, filtros, status da evidência e limitações.
    Lança MissingProvenanceError se qualquer item faltar.
    """
    fmt = format.lower().strip()
    result: Dict[str, Any] = {}

    if fmt == "json":
        parsed = json.loads(content.decode("utf-8"))
        if "provenance" not in parsed:
            raise MissingProvenanceError("REQ-REL-001: Campo 'provenance' ausente no relatório JSON.")
        prov_dict = parsed["provenance"]
        ReportProvenance.from_dict(prov_dict)
        return prov_dict

    elif fmt == "csv":
        text = content.decode("utf-8")
        lines = [line.strip() for line in text.splitlines() if line.startswith("#")]
        meta_dict = {}
        for line in lines:
            if ":" in line:
                key, val = line.lstrip("#").strip().split(":", 1)
                meta_dict[key.strip()] = val.strip()

        # Reconstrução dos tipos
        sources = json.loads(meta_dict.get("sources", "[]"))
        query_date = meta_dict.get("query_date", "")
        versions = json.loads(meta_dict.get("versions", "{}"))
        filters = json.loads(meta_dict.get("filters", "{}"))
        evidence_status = meta_dict.get("evidence_status", "")
        limitations = json.loads(meta_dict.get("limitations", "[]"))

        prov = ReportProvenance(
            sources=sources,
            query_date=query_date,
            versions=versions,
            filters=filters,
            evidence_status=evidence_status,
            limitations=limitations,
        )
        prov.validate()
        return prov.to_dict()

    elif fmt == "pdf":
        text = content.decode("latin1", errors="replace")
        # Checa presença explícita de todos os 6 elementos
        required_patterns = [
            ("sources", r"Fontes:\s*([^\r\n\)]+)"),
            ("query_date", r"Data da Consulta:\s*([^\r\n\)]+)"),
            ("versions", r"Versoes:\s*([^\r\n\)]+)"),
            ("filters", r"Filtros:\s*([^\r\n\)]+)"),
            ("evidence_status", r"Status da Evidencia:\s*([^\r\n\)]+)"),
            ("limitations", r"Limitacoes:\s*([^\r\n\)]+)"),
        ]
        extracted = {}
        for key, pattern in required_patterns:
            match = re.search(pattern, text)
            if not match or not match.group(1).strip():
                raise MissingProvenanceError(f"REQ-REL-001: Item mandatório '{key}' não encontrado no PDF.")
            extracted[key] = match.group(1).strip()
        return extracted

    else:
        raise ValueError(f"Formato não suportado para inspeção: {format}")


def reproduce_report_from_snapshot(
    snapshot: ReportSnapshot,
    format: Literal["json", "csv", "pdf"],
) -> Tuple[bytes, str]:
    """
    Reproduz o relatório de forma idêntica a partir do ReportSnapshot (REQ-REL-002, ACC-REL-002).
    Retorna os bytes do relatório e o hash SHA-256 do conteúdo.
    """
    report_bytes = render_report(snapshot, format)
    report_hash = sha256_digest(report_bytes)
    return report_bytes, report_hash
