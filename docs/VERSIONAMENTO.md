# Versionamento das próximas entregas

A partir de 28/10/2026, por orientação do pesquisador, cada etapa concluída deve receber um commit local após a validação pertinente. O primeiro checkpoint registra o estado existente até a versão 0.19.0; as novas implementações devem ficar em commits separados.

O checkpoint inclui a migração, os módulos operacionais anteriores, a documentação e os artefatos compartilháveis já presentes. A validação Python mais recente desse estado tem 154 testes aprovados; isso não constitui nova validação integral de todos os componentes Java/React do legado.

Não versionar `.env`, credenciais, tokens, bases privadas de curadoria, snapshots operacionais, ambientes virtuais, ferramentas locais ou saídas de execução em `target/`. Os caminhos privados permanecem protegidos pelas regras de `.gitignore`. Artefatos em `docs/resultados/` são entregas compartilháveis deliberadas e devem continuar sem textos integrais ou dados privados de revisão.

Antes de cada commit, conferir o conjunto staged e executar as verificações apropriadas à mudança. O resumo da entrega deve informar o hash do commit e a validação realizada. Commits de software não representam aprovação de revisão humana ou conclusão da pesquisa clínica.

Os artefatos científicos em `docs/resultados/` e os notebooks preservam seus bytes por regras de `.gitattributes`, evitando que conversões automáticas de fim de linha alterem hashes ao versionar ou obter uma cópia do repositório.
