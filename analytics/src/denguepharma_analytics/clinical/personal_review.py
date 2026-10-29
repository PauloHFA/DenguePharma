"""Personal workload derived from current votes; never reserves reviewer slots."""
from collections import Counter

LABELS = {
    'PENDENTE_PARA_MIM': 'Sem minha revisão',
    'REAVALIACAO_NECESSARIA': 'Minha revisão precisa de reavaliação',
    'MINHA_REVISAO_REGISTRADA': 'Minha revisão registrada na base atual',
    'VAGAS_OCUPADAS': 'Duas vagas de revisão já ocupadas',
}


def assignment(actor_id, study_id, state, events):
    own = actor_id in state['votes']
    previous = any(event['kind'] == 'SCREENED' and event['actor'] == actor_id
        and event['payload']['study_id'] == study_id for event in events)
    can_review = own or len(state['votes']) < 2
    status = ('MINHA_REVISAO_REGISTRADA' if own else 'VAGAS_OCUPADAS' if not can_review
        else 'REAVALIACAO_NECESSARIA' if previous else 'PENDENTE_PARA_MIM')
    return dict(status=status, can_review=can_review, has_outdated_own_review=previous and not own)


def summary(assignments):
    counts = Counter(row['status'] for row in assignments)
    return dict(total=len(assignments), current_registered=counts['MINHA_REVISAO_REGISTRADA'],
        first_reviews_pending=counts['PENDENTE_PARA_MIM'],
        reassessments_pending=counts['REAVALIACAO_NECESSARIA'], occupied_slots=counts['VAGAS_OCUPADAS'],
        available_tasks=counts['PENDENTE_PARA_MIM'] + counts['REAVALIACAO_NECESSARIA'],
        notice='Situação da própria conta, sem reserva de vagas. Revisão registrada, inclusive INCERTO, '
            'não equivale a seleção resolvida, calibração ou aprovação de resultados.')


def visible_rows(rows, mode):
    def personal(row):
        # Compatibility for states created before the personal-workload fields.
        return row.get('personal_review') or dict(
            status='MINHA_REVISAO_REGISTRADA' if row.get('own_decision') else 'PENDENTE_PARA_MIM', can_review=True)
    if mode == 'Minha revisão pendente':
        return [row for row in rows if personal(row)['status'] in {'PENDENTE_PARA_MIM', 'REAVALIACAO_NECESSARIA'}]
    if mode == 'Minha revisão registrada':
        return [row for row in rows if personal(row)['status'] == 'MINHA_REVISAO_REGISTRADA']
    if mode == 'Conflitos para adjudicação':
        return [row for row in rows if row.get('can_adjudicate_screening', bool(row.get('adjudication')) and not row.get('own_decision'))]
    return rows
