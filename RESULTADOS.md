# Resultados do experimento

As medições foram feitas sobre um backlog real de uso individual, mantido numa instância própria
de OpenProject. **O conteúdo desse backlog não é publicado**; publicam-se apenas os números
agregados. Para verificar o mecanismo sem depender destes números, o repositório executa o mesmo
método sobre um backlog fictício (ver README, "Reproduza"). Reproduza o método e gere o seu
número.

## Espelhamento da fonte da verdade em três ferramentas (24/09/2026)

Escopo espelhado: 71 itens (11 épicos, 59 tarefas, 1 marco), em 6 sprints de duas semanas.
Fonte: OpenProject 17.8 (self-hosted). Espelhos: Jira Cloud, Trello e GitHub Projects.

| Verificação | Jira | Trello | GitHub Projects |
|---|---|---|---|
| Itens espelhados | 71 | 60 cartões + 11 épicos como etiquetas | 71 issues |
| Segunda execução | 0 criados, 0 atualizados, 71 sem mudança | idem | idem |
| Duplicatas (contadas pelo marcador op:ID) | 0 | 0 | 0 |
| Horas por sprint iguais às da fonte | sim (28/24/27/21/20/16) | sim | sim |

A criação de um projeto no Jira gera, por padrão, uma sprint já ativa e quatro itens de exemplo.
Sem marcador de origem, esses itens não pertencem à fonte e foram removidos antes da medição.

## Custo de tradução por ferramenta

O mesmo método foi representado nas três ferramentas, cada uma com traduções próprias.

| Conceito do método | Jira | GitHub Projects | Trello |
|---|---|---|---|
| Colunas de status | nativo (nomes definidos na criação do projeto) | nativo (opções do campo Status redefinidas pela API) | nativo (listas) |
| Épico e filhos | nativo (campo pai) | nativo (sub-issues com barra de progresso) | inexistente: etiqueta nos filhos |
| Sprint | nativa, com datas | nativa (campo de iteração de 14 dias) | inexistente: etiqueta + data de entrega |
| Estimativa em horas | traduzida: 1 story point = 1 hora | campo numérico | inexistente: sufixo no título |
| Restrição da ferramenta | projeto gerenciado pela equipe não expõe horas | a API não cria visualizações; o quadro é criado manualmente | a API exige área de trabalho e Power-Up |

Em nenhuma das três, na configuração padrão, a regra de WIP ou a exigência de evidência para
concluir são aplicadas. As regras residem fora delas, no código do método.

## Defeitos encontrados durante o experimento

1. **A regra de WIP permanecia inoperante sem sinal de erro.** O adaptador da fonte devolvia o
   número interno do projeto, e a regra buscava o limite pelo identificador. Nenhum limite era
   encontrado, e nenhum movimento era recusado. O defeito foi identificado pela inspeção de
   etiquetas incorretas nos espelhos, não por um teste; daí a sabotagem S1 de
   `testes/sabotagens.sh`.
2. **A identidade dos cartões dependia de um arquivo local.** Quando a ferramenta aceitava uma
   criação e a resposta não chegava ao cliente, a execução seguinte criaria uma duplicata. A
   correção tornou o marcador op:ID, gravado no próprio cartão, a identidade de fato, com
   reconciliação por ele antes de cada criação. Coberto pelo teste
   `test_resposta_perdida_nao_duplica` e pela sabotagem S3.
3. **O vocabulário das colunas estava disperso.** Os nomes dos status apareciam em nove lugares:
   a fonte, os três espelhos, a configuração do método, a skill, um monitor de WIP executado à
   parte (não publicado) e os adaptadores do Trello e do GitHub. No código publicado, a skill e
   os adaptadores leem de `metodo.status_fluxo`; nas ferramentas, os nomes precisam ser
   configurados uma vez para coincidir.

## Medição de uso (28/09/2026 a 02/10/2026)

Mudanças registradas na fonte desde o início da primeira sprint, por autor:

| Autor | Mudanças | Parcela |
|---|---|---|
| Agente (linguagem natural) | 20 | 100% |
| Uso direto da ferramenta | 0 | 0% |

São 20 mudanças em 14 itens. No mesmo período, a primeira sprint registrava 0 h concluídas e 28
h planejadas para 20 h de capacidade, sem o corte de escopo. A medição demonstra que o método
foi operado exclusivamente por conversa; não demonstra progresso da sprint.

## Equivalência entre a versão de uso e a versão publicada (02/10/2026)

Os números acima foram medidos com a versão de uso do código. A versão publicada foi reescrita
sem nenhum nome da instalação de uso. Para verificar que o comportamento se manteve, as duas
versões foram executadas em simulação sobre o mesmo estado:

| Espelho | Versão de uso | Versão publicada |
|---|---|---|
| GitHub | 8 criados, 3 atualizados, 68 sem mudança | 8 criados, 3 atualizados, 68 sem mudança |
| Jira | idem | idem |
| Trello | idem | idem |

As 11 pendências correspondem a alterações feitas na fonte após a primeira carga.

## Auditoria independente (02/10/2026)

Antes da publicação, o repositório foi auditado por uma sessão separada, sem acesso ao backlog
real, em rodadas sucessivas. Em todas, histórico, segredos, dados reais e reprodutibilidade
foram aprovados; o que variou foi o grau de confiança nos testes. Autor e fuso dos commits foram
deixados para decisão do proprietário.

| Rodada | Commit auditado | Defeitos plantados pela auditoria | Detectados pelos testes da época | Outros achados |
|---|---|---|---|---|
| 1 | `5f9bffc` | 8 | 2 | 4 afirmações mais amplas que o código; brecha na DoD (evidência composta só de espaços) |
| 2 | `9f1ebbd` | os 8 anteriores + 6 novos | 8 dos antigos, 0 dos novos | a contagem de "criados" incluía cartões adotados pelo marcador; afirmação mais ampla que o código sobre IDs fixos |
| 3 | `23c6416` | os 15 anteriores + 16 sabotagens dirigidas, uma por afirmação dos textos | 15 dos antigos, 8 das dirigidas | veredito "não pode ir a público": o teste da DoD aceitava um item concluído sem evidência, porque verificava uma palavra que também aparecia no histórico |
| 4 | `25cd503` | os 15 anteriores + 16 dirigidas da rodada 3 + dirigidas ao texto novo | 15 dos antigos, 15 das 16 da rodada 3; 3 afirmações novas sem sabotagem detectada | a fonte externa herdava da fonte local; o título repetido tinha horas diferentes; o espelho externo não era testado |
| 5 | `e838c69` | todas as anteriores + dirigidas ao texto novo | 23 de 23 dirigidas, 15 de 15 antigos; 2 afirmações novas sem sabotagem detectada | a fonte externa expunha atributos internos da fonte local; a saída de `sm projetos` e a sprint de `sm criar` não eram verificadas |
| 6 | `9537c90` | 29 dirigidas das rodadas anteriores + 15 antigos + 3 novas | todas detectadas | nenhum bloqueante ou ressalva; veredito "pode ir a público" |
| 7 | `1f6486c` | somente texto (README reescrito) | — | a afirmação "cada teste é provado por uma sabotagem" não se sustentava: 4 testes nunca falhavam; o script passou a verificar a cobertura e recebeu as sabotagens S37 a S40 |

Cada defeito não detectado e cada brecha resultaram num teste e numa sabotagem (S5 a S40), e os
textos passaram a afirmar apenas o que o código sustenta. O próprio script de sabotagem continha
um alvo ambíguo: um trecho repetido no arquivo era alterado numa ocorrência diferente da
pretendida, e a sabotagem passava sem detecção; o script passou a exigir trechos únicos.

Limite declarado: sempre é possível plantar um defeito que nenhum teste detecta. O critério
adotado é que toda afirmação de comportamento verificável sem conta em ferramenta tenha um
teste, e que esse teste detecte a sabotagem dirigida àquela afirmação. As afirmações sobre as
ferramentas reais (rótulo `op-ID` no Jira, épico como etiqueta no Trello, custos de tradução,
leitura do vocabulário pelos adaptadores, `gh auth login`) são evidência observada no
experimento, declarada como tal: esses adaptadores não têm teste automatizado. A fonte externa
usada nos testes expõe apenas a interface pública, mas delega à implementação local: os testes
demonstram que as regras dependem somente da interface, não que uma fonte real diferente tenha a
mesma semântica.

## Limitação atual

O reflexo é de mão única: mudanças feitas num espelho ainda não retornam à fonte, e as regras do
método ainda não se aplicam a elas. A base para o caminho inverso está implementada: cada
espelho mantém uma cópia de referência de cada item, o que permite determinar qual lado foi
alterado sem depender do relógio de cada ferramenta.

