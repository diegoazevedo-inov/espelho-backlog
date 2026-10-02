# Resultados do experimento

Medições feitas sobre um backlog real de uso individual, mantido numa instância própria de
OpenProject. **O conteúdo desse backlog não é publicado**; publicam-se apenas os números agregados.
Para verificar o mecanismo sem depender destes números, o repositório roda o mesmo método sobre
um backlog fictício (ver README, "Reproduza"). A regra é: reproduza o método e gere o seu número.

## Etapa 1 — a fonte da verdade refletida em três espelhos (24/09/2026)

Escopo espelhado: 71 itens (11 épicos, 59 tarefas, 1 marco), 6 sprints de duas semanas.
Fonte: OpenProject 17.8 (self-hosted). Espelhos: Jira Cloud, Trello e GitHub Projects.

| Verificação | Jira | Trello | GitHub Projects |
|---|---|---|---|
| Itens espelhados | 71 | 60 cartões + 11 épicos como etiquetas | 71 issues |
| Segunda rodada | 0 criados, 0 atualizados, 71 sem mudança | idem | idem |
| Duplicatas (contadas pelo marcador op:ID) | 0 | 0 | 0 |
| Horas por sprint iguais às da fonte | sim (28/24/27/21/20/16) | sim | sim |
| Tempo da primeira carga | 2 min 41 s | 1 min 25 s (após retomada) | vários minutos, com rede instável |

Itens que não vieram da fonte foram tratados como sujeira: o assistente de criação do Jira
gerou uma sprint já ativa e quatro itens de exemplo, removidos depois de confirmado que não
tinham marcador de origem.

## O custo de tradução de cada ferramenta

O mesmo método coube nas três, mas cada uma impôs traduções diferentes.

| Conceito do método | Jira | GitHub Projects | Trello |
|---|---|---|---|
| Colunas de status | nativo (nomes definidos na criação do projeto) | nativo (opções do campo Status redefinidas pela API) | nativo (listas) |
| Épico e filhos | nativo (campo pai) | nativo (sub-issues com barra de progresso) | inexistente: etiqueta nos filhos |
| Sprint | nativa, com datas | nativa (campo de iteração de 14 dias) | inexistente: etiqueta + data de entrega |
| Estimativa em horas | traduzida: 1 story point = 1 hora | campo numérico | inexistente: sufixo no título |
| Limitação imposta | projeto gerenciado pela equipe não expõe horas | a API não cria visualizações; o quadro é criado à mão | API exige área de trabalho e Power-Up |

Em nenhuma das três, na configuração padrão, a regra de WIP ou a exigência de evidência para
concluir são aplicadas. As regras moram fora delas, no código do método.

## Falhas encontradas durante o experimento

1. **A regra de WIP estava desligada sem que nada indicasse.** O adaptador da fonte devolvia o
   número interno do projeto, e a regra procurava o limite pelo identificador. Nenhum limite era
   encontrado, então nenhum movimento era recusado. A falha foi achada ao conferir etiquetas
   erradas nos espelhos, não por um teste — o que motivou o teste S1 de `testes/sabotagens.sh`.
2. **A identidade dos cartões dependia de um arquivo local.** Com a rede instável, a ferramenta
   aceitava a criação e a resposta se perdia; a rodada seguinte criaria uma duplicata. A correção
   foi tornar o marcador op:ID, gravado no próprio cartão, a identidade de fato, e reconciliar por
   ele antes de criar. Coberto pelo teste `test_resposta_perdida_nao_duplica` e pela sabotagem S3.
3. **O vocabulário das colunas estava espalhado.** Os nomes dos status apareciam em nove lugares:
   a fonte, os três espelhos, a configuração do método, a skill, um monitor de WIP que roda à parte
   (não publicado) e os adaptadores do Trello e do GitHub. No código publicado, a skill e os
   adaptadores leem de `metodo.status_fluxo`; nas ferramentas, os nomes precisam ser configurados
   uma vez para coincidir.

## Medição de uso (28/09/2026 a 02/10/2026)

Mudanças registradas na fonte desde o início da primeira sprint, por autor:

| Autor | Mudanças | Parcela |
|---|---|---|
| Agente (linguagem natural) | 20 | 100% |
| Uso direto da ferramenta | 0 | 0% |

20 mudanças em 14 itens. Ressalva registrada com a mesma ênfase: no mesmo período, a primeira
sprint mostrava 0 h concluídas e 28 h planejadas para 20 h de capacidade, sem o corte feito.
A medição prova que o método foi operado só por conversa; não prova que a sprint andou.

## Equivalência do código publicado (02/10/2026)

O código deste repositório foi reescrito sem nenhum nome da instalação original. Para provar que
o comportamento não mudou, as duas versões rodaram em simulação sobre o mesmo estado real:

| Espelho | Código original | Código publicado |
|---|---|---|
| GitHub | 8 criados, 3 atualizados, 68 sem mudança | 8 criados, 3 atualizados, 68 sem mudança |
| Jira | idem | idem |
| Trello | idem | idem |

Os 11 itens pendentes são mudanças reais feitas na fonte depois de 24/09, ainda não espelhadas.

## Auditoria independente (02/10/2026)

Antes da publicação, o repositório foi auditado por uma sessão separada, sem acesso ao backlog
real, em três rodadas. Em todas, histórico, segredos, dados reais e reprodutibilidade foram
aprovados; o que variou foi a confiança nos testes.
Autor e fuso dos commits foram deixados para decisão do dono.

| Rodada | Commit auditado | Defeitos plantados pela auditoria | Pegos pelos testes da época | Outros achados |
|---|---|---|---|---|
| 1 | `5f9bffc` | 8 | 2 | 4 afirmações além do código; brecha na DoD (evidência só com espaços) |
| 2 | `9f1ebbd` | os 8 anteriores + 6 novos | 8 dos antigos, 0 dos novos | contagem de "criados" incluía cartões adotados pelo marcador; um texto absoluto demais sobre IDs no código |
| 3 | `23c6416` | os 15 anteriores + 16 sabotagens dirigidas, uma por afirmação dos textos | 15 dos antigos, 8 das dirigidas | veredito "não pode ir a público": o teste da DoD aceitava o item concluído sem evidência, porque procurava uma palavra que também aparecia no histórico |

Cada defeito que escapou e cada brecha virou um teste e uma sabotagem (S5 a S26), e os textos
passaram a dizer só o que o código sustenta. O próprio script de sabotagem tinha um alvo errado
(um trecho repetido no arquivo, sabotado no lugar errado); passou a exigir trechos únicos.

Limite declarado: sempre é possível plantar um defeito que nenhum teste pega. O critério adotado
aqui é que toda afirmação de comportamento verificável sem conta em ferramenta tenha um teste, e
que esse teste pegue a sabotagem dirigida àquela afirmação. As afirmações sobre as ferramentas
reais (rótulo `op-ID` no Jira, épico como etiqueta no Trello, custos de tradução, leitura do
vocabulário pelos adaptadores, `gh auth login`) são evidência observada no experimento, declarada
como tal: esses adaptadores não têm teste automatizado.

## O que a etapa 1 não demonstra

A volta. Mudanças feitas num espelho ainda não sobem para a fonte, e as regras do método ainda
não são aplicadas a elas. A base existe: cada espelho guarda a cópia de referência de cada item
desde a primeira rodada, que é o que permite saber qual lado mudou. Essa é a etapa 2.
