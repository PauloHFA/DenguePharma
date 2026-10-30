# Alterações e correções de resultados clínicos — versão 0.21.0

Entrega de 29/10/2026. A funcionalidade acrescenta inspeção estrutural e comparação de diferenças entre rascunhos e correções de resultados clínicos (`supersedes`) na curadoria protegida, sem expor trechos literais privados ou decisões semânticas automáticas. Não altera conclusões científicas nem aprova resultados automaticamente.

## Onde está

No [dashboard local](http://127.0.0.1:8501/), acessar **Curadoria clínica — acesso protegido → Extração clínica por campos**:
- Ao marcar **Conferir rascunho sem salvar** em uma correção que substitui um resultado anterior (`supersedes`), o formulário exibe a comparação estrutural antes/depois.
- Na seção **Revisão e adjudicação dos resultados**, ao selecionar um resultado que substitui um anterior, o expander **Alterações desta correção** apresenta as diferenças registradas e alerta caso a base esteja desatualizada.

## Inspeção estrutural e privacidade

A comparação distingue:
1. **Campos científicos**: braços, contagens, médias, desvios padrão, desfecho, período de avaliação, unidade, direção, cuidados de suporte, limitações e domínios de risco de viés.
2. **Campos de fluxo**: vínculo ao estudo (`study_id`), hash da base documental (`basis_hash`), resultado substituído (`supersedes`) e justificativa da correção (`correction_reason`).
3. **Referências documentais**: trechos literais de suporte são representados por hashes (`quote_hash`) e localizadores normalizados (`version_id`, `field`, `text_hash`, `start`, `end`). Nenhum trecho literal privado é exposto nos relatórios de alteração.

## Distinção entre ausência, null e zero

O motor de comparação em `result_changes.py` preserva rigorosamente a semântica de integridade:
- Ausência de campo (`CAMPO_AUSENTE`), valor nulo (`null`) e contagem zero (`0`) são estritamente diferenciados.
- Caminhos JSON utilizam notação RFC 6901 com escape (`~0` para `~` e `~1` para `/`).
- A ordem das referências não afeta a detecção de mudanças (comparação idempotente e independente de ordenação).

## Estado e integridade

A consulta de alterações é somente leitura e não produz novos eventos na auditoria transacional SQLite. Se fontes documentais ou identidades forem alteradas após o rascunho da correção, o indicador `current_basis` informa que a base documental está desatualizada, bloqueando aprovações que dependam de referências antigas.

Resultados iniciais sem predecessor são identificados como `RESULTADO_INICIAL`, sem alterações exibidas.

## Endpoints e contratos

- `GET /api/clinical/{workspace}/results/{result_id}/changes`:
  - Protegido por autenticação Bearer e papéis autorizados de revisão (`REVISOR`, `ADJUDICADOR`, `ADMINISTRADOR`).
  - Cabeçalho obrigatório `Cache-Control: no-store`.
  - Retorno: `result_id`, `predecessor_id`, `current_basis`, `kind`, `field_changes`, `workflow_changes`, `references_changed`, `references_before`, `references_after`, `notice`.

## Resultado nos pilotos reais

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos preservados | 20 | 50 |
| Resultados clínicos revisados | 0 | 0 |
| Avaliações independentes faltantes | 40 | 100 |
| Novos eventos na validação | 0 | 0 |

Os dois pilotos reais permanecem intactos, sem criação artificial de votos ou decisões clínicas.

## Verificação e versionamento

Sete novos testes automatizados em `analytics/tests/test_result_changes.py` cobrem:
- Preservação de ausências, nulos, zeros e caminhos com escape.
- Idempotência de ordem e não exposição de trechos privados nas referências.
- Equivalência entre prévia de correção e alterações salvas sem aprovação prematura.
- Independência entre conferência de diferenças e validação literal de suporte.
- API protegida, somente leitura, com `Cache-Control: no-store` e suporte a resultado inicial.
- Inspeção de alterações mesmo com fontes desatualizadas (`current_basis: false`).
- Componente de interface Streamlit preservando tipos explícitos sem escrita em banco.

A suíte analítica conta agora com **167 testes automatizados** e 100% de aprovação. A matriz mantém 96 requisitos e 29 com evidência automatizada; `REQ-CLN-009` incorpora os cenários de inspeção de alterações.

Esta etapa segue a política de [VERSIONAMENTO.md](VERSIONAMENTO.md), recebendo commit individual após validação.

