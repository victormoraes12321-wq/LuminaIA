# Prompt 13 - Auditoria Pre-Implementacao

Data: 2026-07-30.

## Escopo E Autoridades Existentes

- `EnterpriseKnowledgeService` e `EnterpriseKnowledgeRuntime` entregam somente
  assets publicados, vigentes e tenant-scoped. Esta e a fonte governada para
  conceitos, aliases, relacoes e IDs semanticos.
- `services.metric_registry.METRIC_DEFINITIONS` continua sendo a autoridade
  numerica. A recuperacao semantica pode validar uma referencia, mas nunca
  copiar, alterar ou executar formulas.
- O catalogo analitico PostgreSQL e a unica fonte permitida para instancias de
  entidades. Oracle, banco operacional, SQL livre e colunas escolhidas pelo
  cliente ficam fora da indexacao.
- `ContextResolutionEngine` continua sendo a autoridade para heranca,
  correcao, remocao, branches e contexto ativo.
- `UserAnalyticalProfile` pode participar somente como desempate fraco e
  opt-in entre candidatos ja validos.
- Feedback supervisionado aprovado pode alimentar corpus offline e
  evaluations, mas nao altera pesos, aliases ou indice publicado.

## Fontes Semanticas E Aliases Atuais

- O catalogo estatico de `services.metadata_catalog` contem entidades,
  metricas, dimensoes e aliases globais usados pelo pipeline legado.
- `services.semantic_layer` possui dicionarios estaticos, sinonimos e
  similaridade por `SequenceMatcher`.
- Enterprise Knowledge v13 persiste assets, versoes, aliases e relacoes
  publicados com tenant, checksum, lifecycle e vigencia.
- `SemanticMemory` legado persiste expressoes e objetos resolvidos por tenant,
  inclusive com origem `IA`; nao possui workflow de publicacao e nao e fonte
  empresarial confiavel.
- `BusinessConcept`, `SemanticCatalog` e metadados tecnicos antigos se
  sobrepoem parcialmente, mas nao substituem Enterprise Knowledge.

## Canonical IDs E Entidades Atuais

- Metricas oficiais usam chaves de `MetricRegistry`, como
  `faturamento_comercial`, `ticket_medio`, `saida_rb` e `devolucao`.
- Knowledge Base usa `canonical_key` por tenant e tipo de asset.
- O pipeline legado tambem usa nomes conceituais como `Venda.Receita`,
  `Cliente.cidade` e `Produto.familia`.
- Instancias de filial, produto, cliente, fornecedor e vendedor ainda nao
  possuem um indice semantico governado e versionado.

## Riscos Confirmados No Codigo Executado

1. `SemanticCanonicalizer` muta o `SemanticPlan` recebido e aplica fallbacks
   por palavras-chave.
2. Alguns fallbacks escolhem o primeiro grupo reconhecido, sem threshold,
   margem ou representacao de ambiguity.
3. `services.semantic_layer._resolve_metric_by_safe_similarity` preserva apenas
   o melhor candidato e retorna automaticamente acima de um limite fixo.
4. O fallback de erro do intent engine cria uma entidade `Cliente`, o que pode
   trocar silenciosamente o assunto.
5. O intent legado envia o catalogo estatico ao modelo. O Prompt 13 nao fara
   chamada adicional e limitará qualquer projecao futura a candidatos
   permitidos.
6. `SemanticMemory` captura erros de repository de forma permissiva e pode
   incrementar frequencia ou gravar resolucao sem review.
7. Caches legados nao carregam necessariamente index version, policy version,
   permission fingerprint e contexto na mesma identidade.
8. O caminho critico `vw_vendas_lm` ainda nao comprova `tenant_id` na view;
   essa fonte nao sera usada para indexar entidades sem isolamento verificavel.

## Privacidade

- CPF, RG, CNPJ pessoal, e-mail, telefone, endereco, nascimento, senha, token,
  cookie, credencial e connection string nao podem virar termo, alias ou
  representacao.
- CUSTOMER, SELLER e outras entidades potencialmente pessoais permanecem
  desabilitadas sem policy explicita e permission fingerprint.
- Pergunta, conversa, SearchHistory, SQL, binds, datasets, prompts e vetores
  brutos nao serao persistidos no indice.

## Capacidades Tecnicas Auditadas

- Nao ha dependencia `pgvector`, provider neural local aprovado ou modelo
  offline instalado.
- Nao ha uso atual governado de `pg_trgm` ou `tsvector`.
- PostgreSQL possui JSONB, arrays, indices GIN e transacoes; extensoes
  opcionais nao serao habilitadas automaticamente.
- O provider escolhido e `DETERMINISTIC_FEATURE_HASH`, com SHA-256,
  character n-grams, tokens, dimensao fixa, normalizacao L2 e cosine.
- A recuperacao lexical e o matching publicado continuam primarios. O canal de
  representacao opera apenas sobre um conjunto lexical limitado.
- O mecanismo de migrations e ad hoc, explicito e versionado. A proxima
  migration sera v16, aditiva e com down guardado para banco descartavel.
- Existem schedulers e background tasks, mas nao um worker duravel governado
  para esse build. O build inicial sera transacional e limitado; job duravel
  permanece item de rollout.

## Decisao De Implementacao

Criar `lumina.semantic-retrieval/1.0` como uma unica fronteira que inclui
recuperacao hibrida e entity resolution. Contratos distinguirao documents,
representations, policies, candidatos, decisoes e patches. O runtime novo sera
tenant-scoped, fail-closed, desligado por padrao e integrado por adapters; o
canonicalizer, SemanticMemory e fallbacks existentes permanecerao somente para
rollback nos modos permitidos.
