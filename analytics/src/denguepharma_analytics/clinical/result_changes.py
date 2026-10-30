"""Read-only correction differences; no conclusions and no literal evidence quotes."""
from ..domain import digest,json_bytes
from .workspace import REVIEW_ROLES

WORKFLOW_FIELDS={'study_id','basis_hash','supersedes','correction_reason'}
NOTICE='Comparação estrutural dos rascunhos, sem julgamento de significado clínico. '
NOTICE+='Ausência, null e zero são distintos. Trechos literais são representados por hashes e localizadores; '
NOTICE+='a conferência das fontes e a revisão independente continuam obrigatórias.'


def differences(before,after):
    changes=[]
    def visit(old,new,path):
        if isinstance(old,dict) and isinstance(new,dict):
            for key in sorted(set(old)|set(new)):
                pointer=path+'/'+key.replace('~','~0').replace('/','~1')
                if key not in old or key not in new:
                    changes.append(dict(path=pointer,before_exists=key in old,after_exists=key in new,
                        before=old.get(key),after=new.get(key)))
                else:visit(old[key],new[key],pointer)
        elif json_bytes(old)!=json_bytes(new):
            changes.append(dict(path=path,before_exists=True,after_exists=True,before=old,after=new))
    visit(before,after,'')
    return changes


def references(data):
    rows=[]
    for ref in data.get('evidence',[]):
        rows.append({k:ref[k] for k in ('field','version_id','text_hash','start','end')}|
            {'quote_hash':digest(ref['quote'].encode())})
    return sorted(rows,key=json_bytes)


def compare(before,after):
    scientific=lambda data:{k:v for k,v in data.items() if k not in WORKFLOW_FIELDS|{'evidence'}}
    workflow=lambda data:{k:v for k,v in data.items() if k in WORKFLOW_FIELDS}
    old_refs,new_refs=references(before),references(after)
    return dict(field_changes=differences(scientific(before),scientific(after)),
        workflow_changes=differences(workflow(before),workflow(after)),
        references_changed=old_refs!=new_refs,references_before=old_refs,references_after=new_refs,notice=NOTICE)


def predecessor(events,data):
    prior=next((e for e in events if e['kind']=='RESULT_DRAFTED' and e['id']==data.get('supersedes')),None)
    if data.get('supersedes') and prior is None:raise ValueError('UNKNOWN_SUPERSEDED_RESULT')
    return prior


def view(workspace,result_id,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db)
        current=next((e for e in events if e['kind']=='RESULT_DRAFTED' and e['id']==result_id),None)
        if not current:raise ValueError('RESULT_NOT_FOUND')
        data=current['payload'];prior=predecessor(events,data)
        try:workspace.validate_result(db,data,events);current_basis=True
        except ValueError:current_basis=False
        return dict(result_id=result_id,predecessor_id=prior['id'] if prior else None,
            current_basis=current_basis,kind='CORRECAO' if prior else 'RESULTADO_INICIAL',
            **(compare(prior['payload'],data) if prior else dict(field_changes=[],workflow_changes=[],
                references_changed=False,references_before=[],references_after=[],notice=NOTICE)))
