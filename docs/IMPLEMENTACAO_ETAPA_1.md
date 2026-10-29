# Etapa 1 — Fluxos de curadoria e proteção da publicação

Data: 27/10/2026. Implementação posterior à [auditoria inicial](AUDITORIA_REQUISITOS.md), que permanece como registro do estado encontrado.

Atualização: a conexão de armazenamento, broker e workers foi implementada posteriormente na [etapa 2](IMPLEMENTACAO_ETAPA_2.md). As pendências abaixo registram o estado ao concluir a etapa 1.

## Mudanças entregues

- Revisão alinhada aos nomes de campos e enums do backend. A tela exibe valor original, trecho, seção, página, localizador, versão e texto disponível da fonte.
- Correções exigem justificativa escrita e, para valor presente, um trecho literal da versão documental. A API verifica o texto decodificado, gera um novo span com posição e não cria evidência a partir da justificativa. A auditoria preserva corretamente valores com aspas e quebras de linha.
- Campos críticos corrigidos/aceitos por REVISOR ficam em `EM_REVISAO`, sem publicação; publicar ou alterar campo crítico aprovado exige ADJUDICADOR/ADMINISTRADOR. A decisão é protegida por bloqueio transacional do campo. Estados `INCERTO` e `NAO_EXTRAIDO` não podem ser publicados.
- Triagem mostra resumo/texto disponível, permite classificar contexto/finalidade, registrar ausência de resultados e selecionar motivo de exclusão. Deixou de enviar `HUMANO/TRATAMENTO` fixos e justificativa genérica.
- Comparador mostra a mensagem de incompatibilidade retornada pela API e impede consulta de estudos fora do catálogo vigente. IDs repetidos não atendem ao mínimo de dois estudos distintos.
- PDF/CSV são baixados com Bearer token; falhas aparecem na tela. O cliente aceita respostas HTTP 200 sem corpo e apresenta detalhes de validação da API.
- PDF passou a quebrar linhas e gerar páginas adicionais, sem truncar as linhas em 105 caracteres. CSV passou a incluir filtros do snapshot.
- Acesso aberto sem licença explícita permanece com licença `NAO_VERIFICADA`, sem autorização presumida de redistribuição.
- Catálogo exige inclusão na triagem e ao menos um campo aprovado/publicado. Estudos excluídos, absorvidos, retratados e demonstrativos ficam fora do catálogo/comparador e de novos snapshots.
- Semente de 20 registros identificada como demonstração na interface e no banco (`is_demo`). A migration V6 identifica também os registros antigos gerados pela semente, sem apagar dados ou snapshots históricos.

## Validação

- Backend: 41 testes, incluindo regressões de autorização, correção sem suporte, texto com escapes, isolamento de catálogo, licença desconhecida e relatórios com múltiplas páginas.
- Frontend: 14 testes, incluindo aprovação/correção com o contrato da API, encaminhamento ao adjudicador, texto de incompatibilidade, download autenticado e preservação do contexto na triagem.
- Compilação de produção TypeScript/Vite.

Os testes da interface usam respostas simuladas no formato do backend. Não substituem homologação em navegador com uma base real. O teste de PDF verifica estrutura, paginação e preservação de conteúdo; não houve inspeção visual renderizada nesta etapa.

## Como aplicar

Inicie o backend normalmente com a configuração local existente; o Flyway aplica V6. Reinicie a interface para carregar as alterações. Não são necessárias novas credenciais para esta etapa.

O catálogo pode ficar vazio se a base contiver apenas demonstrações ou estudos sem campos revisados/publicados. Isso evita apresentar a semente sintética como evidência científica. Snapshots históricos continuam preservados, inclusive os que já continham dados demonstrativos.

## Pendências preservadas para as próximas etapas

1. Conectar MinIO, RabbitMQ e workers a uma execução real, com persistência protegida pelo lease, retentativas e integração de modelo configurável.
2. Recuperar e revisar o piloto científico por fontes reais; demonstrações ainda precisam ser excluídas também das rotinas experimentais e do pacote de reprodução.
3. Completar dicionário e formulários de resultados por braço/desfecho. Exigir proveniência/revisão por atributo exibido: nesta etapa o catálogo exige pelo menos um campo publicado, mas os resumos em `study` ainda precisam ser reconciliados com as aprovações individuais.
4. Completar comparabilidade de população, intervenção, sorotipo, comparador e definição do desfecho; tratar dados insuficientes sem declarar compatibilidade indevida.
5. Normalizar namespaces de identificadores entre fontes, obter texto integral permitido e implementar atualização periódica, erratas e retratações automáticas.
6. Corrigir as métricas científicas e o desenho experimental, incluindo referência independente adjudicada, congelamento efetivo, randomização e intervalos de confiança.
7. Completar administração, reprodução, backup/restauração, desempenho, acessibilidade e homologação ponta a ponta.

Verificar a presença literal de um trecho não prova automaticamente que ele sustenta semanticamente um valor corrigido. A conferência desse vínculo permanece responsabilidade da revisão humana.

## Registro final das alterações posteriores

As pendências acima descrevem o encerramento histórico da etapa 1. O projeto evoluiu para ciência de dados com dashboards abertos, pipeline real, snapshots analíticos e coleta piloto. O escopo vigente está nos [Requisitos v3](REQUISITOS_V3.md).

O **[registro consolidado das etapas 1 a 4](ALTERACOES_CONSOLIDADAS.md)** documenta todas essas alterações, interfaces, migrations, análises, testes e limites. A [validação do piloto](TESTE_CIENCIA_DADOS.md) separa o que foi executado do que ainda depende de revisão humana. O experimento com IA foi adiado e não deve ser interpretado como pendência obrigatória do MVP atual.
