"""Operational coverage of reviewed outcomes, never inferred outcome availability."""
from io import BytesIO
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

from .. import __version__
from ..domain import digest,json_bytes
from .workspace import REVIEW_ROLES
from .review import csv_bytes


def view(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db);catalog=workspace.catalog(events)
        approved,_,conflicts=workspace.results(db,events)
        drafts={e['id']:e['payload'] for e in events if e['kind']=='RESULT_DRAFTED'}
        conflict_cells={(drafts[i]['study_id'],drafts[i]['outcome_code']) for conflict in conflicts for i in conflict['result_ids']}
        cells=[];included=0
        for study,documents in sorted(catalog.items()):
            state=workspace.screening(db,study,events)
            if state['status']!='INCLUIR':continue
            included+=1
            for outcome,domain in workspace.protocol['outcomes'].items():
                results=[r for r in approved if r['study_id']==study and r['outcome_code']==outcome]
                conflicting=(study,outcome) in conflict_cells
                cells.append(dict(study_id=study,title=documents[0].get('title') or '',basis_hash=state['basis_hash'],
                    population=state['classification']['population'],design=state['classification']['design'],
                    outcome_code=outcome,outcome_domain=domain,reviewed_result_count=len(results),
                    reviewed_comparison_count=len({r['comparison_id'] for r in results}),
                    result_ids=sorted(r['result_id'] for r in results),has_conflict=conflicting,
                    status='CONFLITO_PENDENTE' if conflicting else 'COM_RESULTADO_REVISADO' if results else 'SEM_RESULTADO_REVISADO'))
        selection=workspace.selection_hash(db,events)
        return dict(schema_version='clinical-extraction-coverage-1',workspace_id=workspace.key,
            input_hash=workspace.input.input_hash,protocol_hash=digest(json_bytes(workspace.protocol)),selection_hash=selection,
            audit_head=events[-1]['event_hash'] if events else '0'*64,
            unit='identidade_incluida_x_desfecho_do_protocolo',included_studies=included,protocol_outcomes=len(workspace.protocol['outcomes']),
            cells=cells,cells_with_reviewed_results=sum(c['reviewed_result_count']>0 for c in cells),
            cells_without_reviewed_results=sum(c['reviewed_result_count']==0 for c in cells),
            cells_with_conflicts=sum(c['has_conflict'] for c in cells),
            calibration_approved=any(e['kind']=='CALIBRATION_APPROVED' and e['payload']['basis_hash']==selection for e in events),
            notice='Mapa de trabalho da curadoria, não mapa de eficácia ou completude científica. '
                'Sem resultado revisado não significa desfecho não medido, não aplicável, zero eventos ou ausência de benefício. '
                'Rascunhos não contam como revisão. Cada célula pode reunir comparações e estratos diferentes; não soma participantes ou efeitos. '
                'Conflitos podem coexistir com outros resultados revisados na mesma célula. Publicação e julgamento clínico continuam separados.')


def package(workspace,actor):
    report=view(workspace,actor)
    from ..storage import code_hash
    rows=[dict(**{k:v for k,v in cell.items() if k!='result_ids'},result_ids_json=json_bytes(cell['result_ids']).decode()) for cell in report['cells']]
    columns=['study_id','title','basis_hash','population','design','outcome_code','outcome_domain',
        'reviewed_result_count','reviewed_comparison_count','has_conflict','status','result_ids_json']
    summary={k:v for k,v in report.items() if k!='cells'}
    files={'coverage.csv':csv_bytes(rows,columns),'summary.json':json_bytes(summary)}
    files['manifest.json']=json_bytes(dict(schema_version='clinical-extraction-coverage-package-1',
        version=__version__,code_hash=code_hash(),workspace_id=workspace.key,input_hash=report['input_hash'],
        protocol_hash=report['protocol_hash'],selection_hash=report['selection_hash'],audit_head=report['audit_head'],
        artifacts={name:digest(content) for name,content in files.items()}))
    output=BytesIO()
    with ZipFile(output,'w') as archive:
        for name,content in sorted(files.items()):
            info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o600<<16
            archive.writestr(info,content)
    return output.getvalue()
