"""Read-only documentary context for independent screening; no votes or suggestions."""
from ..domain import digest
from .workspace import REVIEW_ROLES
from .integrity import blocked_documents


def view(workspace, study_id, actor, *, expected_basis=None):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events = workspace.events(db)
        documents = workspace.catalog(events).get(study_id)
        if not documents:
            raise ValueError('UNKNOWN_STUDY')
        basis = workspace.basis(db, study_id, events)
        if expected_basis is not None and expected_basis != basis:
            raise ValueError('STALE_STUDY_BASIS')
        by_id = {d['documentId']: d for d in documents}
        sources = []
        for row in db.execute('SELECT * FROM sources ORDER BY document_id, version_id'):
            if row['document_id'] not in by_id:
                continue
            document = by_id[row['document_id']]
            if digest(row['text'].encode()) != row['text_hash']:
                raise ValueError('SOURCE_TEXT_HASH_MISMATCH')
            if row['content_hash'] != document['contentHash']:
                raise ValueError('SOURCE_CONTENT_HASH_MISMATCH')
            sources.append({name: row[name] for name in
                ('document_id', 'version_id', 'content_hash', 'text_hash', 'license', 'access')})
        rows = []
        for document in sorted(documents, key=lambda d: d['documentId']):
            metadata = document.get('metadata', {})
            identifiers = {name: metadata[name] for name in ('pmid', 'pmcid', 'doi')
                if isinstance(metadata.get(name), str) and metadata[name].strip()}
            nct = metadata.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
            if isinstance(nct, str) and nct.strip():
                identifiers['nct'] = nct
            rows.append({
                'document_id': document['documentId'], 'title': document.get('title'),
                'source': document.get('source'), 'document_type': document.get('documentType'),
                'original_version_id': document['versionId'], 'version': document.get('version'),
                'retrieved_at': document.get('retrievedAt'), 'identifiers': identifiers,
                'source_versions': [s for s in sources if s['document_id'] == document['documentId']],
            })
        return {
            'workspace_id': workspace.key, 'study_id': study_id, 'basis_hash': basis,
            'input_hash': workspace.input.input_hash, 'documents': rows,
            'unresolved_identity_documents': sorted(set(by_id).intersection(workspace.unresolved_identity(events))),
            'integrity_alerts': {key:value for key,value in blocked_documents(events).items() if key in by_id},
            'notice': 'Contexto documental privado, sem votos ou sugestões de elegibilidade. '
                'Representações textuais não equivalem a documentos ou estudos adicionais. '
                'Texto disponível não comprova acesso a texto integral ou permissão de redistribuição.',
        }
