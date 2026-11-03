"""Private selection accounting; annotations never replace independent screening."""
from collections import Counter
from typing import Literal

from pydantic import Field
from ..domain import digest, json_bytes
from .models import Strict
from .workspace import ADJUDICATORS, REVIEW_ROLES

CATEGORIES = {
    'POPULACAO_FORA_ESCOPO': 'População fora do escopo',
    'CONTEXTO_FORA_ESCOPO': 'Contexto fora do escopo clínico',
    'INTERVENCAO_NAO_ELEGIVEL': 'Intervenção fora do escopo farmacológico',
    'DESENHO_NAO_ELEGIVEL': 'Desenho não elegível',
    'OUTRO_CRITERIO_PROTOCOLO': 'Outro critério explícito do protocolo',
}
DICTIONARY = 'clinical-exclusion-reasons-1'


class ExclusionReason(Strict):
    study_id: str
    resolution_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    category: Literal['POPULACAO_FORA_ESCOPO', 'CONTEXTO_FORA_ESCOPO',
        'INTERVENCAO_NAO_ELEGIVEL', 'DESENHO_NAO_ELEGIVEL', 'OUTRO_CRITERIO_PROTOCOLO']
    reason: str = Field(min_length=10)


def resolution(workspace, db, study, events):
    state = workspace.screening(db, study, events)
    adjudication = next((event['id'] for event in reversed(events)
        if event['kind'] == 'SCREEN_ADJUDICATED'
        and event['payload']['study_id'] == study
        and event['payload']['basis_hash'] == state['basis_hash']
        and event['payload']['votes_hash'] == state['votes_hash']), None)
    token = digest(json_bytes({
        'basis_hash': state['basis_hash'], 'votes_hash': state['votes_hash'],
        'status': state['status'], 'classification': state['classification'],
        'adjudication_id': adjudication,
    }))
    return state, token


def validate(workspace, db, payload, actor, events):
    actor.require(*ADJUDICATORS)
    data = ExclusionReason.model_validate(payload).model_dump()
    state, token = resolution(workspace, db, data['study_id'], events)
    if state['status'] != 'EXCLUIR':
        raise ValueError('RESOLVED_EXCLUSION_REQUIRED')
    if data['resolution_hash'] != token:
        raise ValueError('STALE_EXCLUSION_RESOLUTION')
    documents = workspace.catalog(events)[data['study_id']]
    if set(workspace.unresolved_identity(events)).intersection(d['documentId'] for d in documents):
        raise ValueError('AMBIGUOUS_DOCUMENT_IDENTITY')
    return {**data, 'dictionary_version': DICTIONARY}


def view(workspace, actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events = workspace.events(db)
        catalog = workspace.catalog(events)
        status_counts, reasons = Counter(), Counter()
        editable = bool(set(actor.roles).intersection(ADJUDICATORS))
        excluded, pending_reasons = [], 0
        latest = {event['payload']['study_id']: event for event in events
            if event['kind'] == 'EXCLUSION_REASON_RECORDED'}
        ambiguous = set(workspace.unresolved_identity(events))
        for study, documents in sorted(catalog.items()):
            state, token = resolution(workspace, db, study, events)
            status_counts[state['status']] += 1
            if state['status'] != 'EXCLUIR':
                continue
            event = latest.get(study)
            current = bool(event and event['payload']['resolution_hash'] == token
                and event['payload']['dictionary_version'] == DICTIONARY
                and not ambiguous.intersection(d['documentId'] for d in documents))
            if current:
                reasons[event['payload']['category']] += 1
            else:
                pending_reasons += 1
            if editable:
                excluded.append(dict(study_id=study, title=documents[0].get('title'),
                    resolution_hash=token, can_record=not bool(ambiguous.intersection(d['documentId'] for d in documents)),
                    annotation=event['payload'] if current else None))
        counts = {name: status_counts[name] for name in ('PENDENTE', 'INCERTO', 'CONFLITO', 'INCLUIR', 'EXCLUIR')}
        assert sum(counts.values()) == len(catalog)
        assert sum(reasons.values()) + pending_reasons == counts['EXCLUIR']
        return dict(schema_version='clinical-selection-flow-1', workspace_id=workspace.key,
            input_hash=workspace.input.input_hash, protocol_hash=digest(json_bytes(workspace.protocol)),
            selection_hash=workspace.selection_hash(db, events),
            audit_head=events[-1]['event_hash'] if events else '0'*64,
            dictionary_version=DICTIONARY, document_count=len(workspace.input.data['documents']),
            study_identity_count=len(catalog), statuses=counts,
            exclusion_reasons=[dict(category=category, label=label, count=reasons[category]) for category, label in CATEGORIES.items()],
            exclusions_without_current_reason=pending_reasons,
            unresolved_identity_documents=len(ambiguous),
            selection_complete=bool(catalog) and not ambiguous and not any(counts[name] for name in ('PENDENTE', 'INCERTO', 'CONFLITO')),
            identification=dict(identified_records=None, removed_duplicates=None, screened_records=None,
                status='NAO_RECONSTRUIDO_PARA_O_PILOTO'),
            can_record=editable, excluded_studies=excluded,
            notice='Resumo operacional privado, não um fluxograma PRISMA completo. '
                'Identidades de estudo não são registros identificados, documentos duplicados ou estudos elegíveis. '
                'Somente exclusões resolvidas recebem um motivo principal humano. '
                'Ausência de texto integral não é motivo de exclusão. Campos não reconstruídos permanecem nulos.')


def export_summary(workspace, actor):
    data = view(workspace, actor)
    # Uniform aggregate export, even for adjudicators; no study decisions or justifications.
    return {key: value for key, value in data.items() if key not in ('excluded_studies', 'can_record')}


def compute_prisma_flow(
    identified_records: int,
    duplicates_removed: int,
    screened_records: int,
    included_records: int,
    exclusion_reasons: dict[str, int],
) -> dict:
    """Gera contagens consistentes do fluxograma PRISMA-ScR (REQ-SEL-004).

    Garante a igualdade contábil fundamental exigida pelo critério de aceitação:
    identificados = duplicados + triados
    triados = incluidos + excluidos
    exclusoes = soma das categorias de exclusao
    """
    if identified_records != duplicates_removed + screened_records:
        raise ValueError(
            f"Inconsistência contábil PRISMA-ScR: identificados ({identified_records}) "
            f"deve ser igual a duplicados ({duplicates_removed}) + triados ({screened_records})."
        )
    total_excluded = sum(exclusion_reasons.values())
    if screened_records != included_records + total_excluded:
        raise ValueError(
            f"Inconsistência contábil PRISMA-ScR: triados ({screened_records}) "
            f"deve ser igual a incluídos ({included_records}) + exclusões ({total_excluded})."
        )
    return {
        "identified_records": identified_records,
        "duplicates_removed": duplicates_removed,
        "screened_records": screened_records,
        "included_records": included_records,
        "excluded_records": total_excluded,
        "exclusion_reasons": exclusion_reasons,
        "formula_verified": True,
        "notice": "Fluxograma estruturado conforme recomendação PRISMA-ScR (Tricco et al., 2018).",
    }
