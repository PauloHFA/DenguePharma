# Dossiê documental na triagem — versão 0.15.0

Entrega de 28/10/2026. A triagem clínica agora reúne os documentos e as representações textuais do estudo selecionado, no próprio formulário. O objetivo é facilitar a leitura humana das fontes antes da decisão independente.

## Como usar

1. Abrir o [dashboard local](http://127.0.0.1:8501/).
2. Expandir **Curadoria clínica — acesso protegido** e entrar com a própria conta.
3. Selecionar o espaço clínico com 20 documentos.
4. Em **Triagem por campos — revisão humana**, escolher o estudo e expandir **Documentos do estudo selecionado — leitura para triagem**.
5. Conferir documentos, identificadores, versões, hashes, licença e acesso registrados. Selecionar **Fonte deste estudo** e marcar **Ler texto normalizado desta versão**.
6. Ler o material permitido e preencher a própria classificação, decisão e justificativa no formulário existente. Quando necessário, usar **Fontes permitidas e localizadores** para gerar referências literais.

Representações diferentes do mesmo documento são preservadas. Elas não acrescentam estudos ou documentos à contagem. O texto normalizado pode conter somente metadados ou resumo; sua presença não comprova texto integral, licença para redistribuição ou suporte semântico. Materiais ausentes continuam ausentes.

## Contrato e integridade

Consulta autenticada: `GET /api/clinical/{workspace}/studies/{study_id}/dossier?basis_hash=HASH_ATUAL`.

A API exige os papéis já autorizados para revisão, retorna `Cache-Control: no-store` e restringe as versões aos documentos da identidade atual do estudo. Não inclui votos, autores de decisões, classificações humanas, sugestões de elegibilidade, texto da fonte ou dados brutos irrestritos. O texto só é solicitado explicitamente pela interface de fontes autenticada existente. Essa representação permanece na área privada.

O parâmetro opcional `basis_hash`, sempre enviado pelo formulário, detecta alteração dos documentos, representações ou identidade desde a carga da fila. Uma base desatualizada retorna `409`; estudo desconhecido retorna `404`; ausência de autenticação retorna `401`, e papel não autorizado, `403`. São conferidos os hashes do texto normalizado e do conteúdo original associado ao documento. A verificação não constitui julgamento de qualidade científica.

Identidades legadas ambíguas são sinalizadas. A consulta não corrige vínculos, cria fontes ou votos, adjudica divergências, aprova calibração, inicia coleta ou publica evidências.

## Verificação real e resultados

| Espaço | Documentos | Representações textuais | Votos independentes faltantes | Novos eventos de decisão |
| --- | --- | --- | --- | --- |
| Piloto clínico | 20 | 50 | 40 | 0 |
| Piloto operacional | 50 | 125 | 100 | 0 |

Todos os estudos/identidades de ambos os espaços foram consultados sem duplicação de documentos ou alteração dos eventos existentes. Os números descrevem os espaços operacionais, sem afirmar elegibilidade clínica. As calibrações permanecem não aprovadas. A autenticação real e o contrato privado também foram conferidos na API local.

No Chrome, o teste com autenticação real confirmou a abertura do dossiê e do texto normalizado, a presença do formulário de triagem e a retirada do contexto privado após sair. Nenhum botão de gravação de decisão foi acionado e não houve erro de página.

Foram acrescentados seis casos automatizados, incluindo dois de corrupção de fonte. A bateria completa teve 122 aprovações e uma falha no mock antigo do formulário, que não previa a nova consulta documental. O mock foi atualizado para distinguir leitura e gravação; o caso foi reexecutado e aprovado. Assim, os 123 casos têm aprovação registrada, com a falha inicial preservada no JUnit combinado. Nenhuma transformação analítica mudou em resposta à falha.

Os testes cobrem cegamento, escopo por estudo, permissão, leitura sem escrita, atualização de fontes, mudança de identidade, ambiguidade, material ausente, integridade de hashes e importação/revisão existentes. A execução completa incluiu PostgreSQL e Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada; o requisito CLN-008 foi ampliado, sem promover a execução científica como concluída.

Evidências técnicas locais, fora do versionamento: `analytics/target/dossier-real-results.json`, `analytics/target/dossier-evidence-junit.xml` e `analytics/target/dossier-browser-results.json`.

## O que continua pendente

O próximo marco científico é a revisão independente das fontes. No piloto clínico faltam 40 avaliações, seguidas da adjudicação das divergências, calibração e extração/revisão de resultados elegíveis. Não foi gerada conclusão sobre benefício ou dano de medicamentos.

Os [relatórios científicos publicados](resultados/pesquisa-reprodutivel/README.md) continuam vinculados às execuções 0.14.0 anteriores. Esta entrega atualiza somente a curadoria e sua interface; não refaz snapshots ou relatórios históricos para aparentar resultados novos.
