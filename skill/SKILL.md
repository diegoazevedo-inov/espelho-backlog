---
name: scrum
description: Opera um método Scrum/Kanban por linguagem natural — sprints, daily, planning, review, retro, WIP, Definition of Done, criar/mover/comentar itens e consultar o estado de projetos. Use quando a conversa falar de tarefa, item, sprint, backlog, quadro, kanban, "o que tenho pra fazer", "terminei X", "comecei Y", daily, planning, revisão ou retrospectiva. Quem usa não abre a ferramenta de gestão; tudo passa por aqui.
---

# Método Scrum/Kanban operado por conversa

Premissa: o método importa mais que a ferramenta. A ferramenta de gestão é vitrine; a interface
é a conversa. Nunca responder "abra a ferramenta e…": fazer pelo `sm`.

O método está no comando **`sm`** e nesta skill. A ferramenta é um adaptador trocável, definido na
configuração (`ESPELHO_CONFIG`). Toda mudança feita por aqui sai com o autor configurado em
`metodo.autor_agente`, e é isso que permite medir o uso (`sm prova`).

## Comandos

```
sm projetos
sm itens [-p PROJ] [--status S...] [--sprint S1] [--tipo Épico] [--busca txt] [--todos]
sm ver ID                                     # detalhe + histórico (dailies, evidências)
sm sprint [-p PROJ] [S2]                      # horas × capacidade, itens por coluna
sm wip [-p PROJ]
sm criar [-p PROJ] "assunto" [--pai ID] [--horas N] [--prioridade Alta] [--sprint S1] [--desc "..."]
sm mover ID "<status>" [--nota "..."]         # recusa se o WIP estiver cheio
sm mover ID "<status final>" --evidencia "..." [--ressalva "..."]   # sem evidência, recusa
sm comentar ID "texto"
sm editar ID [--assunto] [--horas] [--prioridade] [--sprint S2 | --sprint ''] [--pai ID]
sm prova [--desde AAAA-MM-DD]
```

Os nomes das colunas, o limite de WIP, a capacidade e o projeto padrão vêm da configuração
(`metodo`). A skill não fixa nenhum deles.

## Regras do método

- **Definition of Ready** — só sai do backlog com: objetivo em uma frase, critério de aceitação
  verificável, estimativa em horas, nenhuma dependência aberta. Se faltar, perguntar antes de mover.
- **Definition of Done** — para o status final:
  1. critério de aceitação verificado no artefato, não no relato;
  2. evidência registrada (saída de comando, link, captura, número) em `--evidencia`;
  3. onde houver verificação automática: defeito plantado e detector visto vermelho;
  4. nada identificável de terceiros no que for público;
  5. ressalvas registradas em `--ressalva`.
  "Terminei X" sem evidência: pedir a evidência, não marcar pelo relato.
- **WIP** — respeitar o limite configurado. Coluna cheia: mostrar o que ocupa e perguntar o que sai.
  `--forcar` só com decisão explícita, e a exceção fica registrada no item.
- **Capacidade** — `sm sprint` mostra o excesso. Nunca planejar acima sem decisão explícita do corte.

## Cerimônias

- **Planning**: `sm sprint <S>` → horas × capacidade; se exceder, propor o corte (menor prioridade
  primeiro) e esperar a decisão; aplicar com `sm editar ID --sprint <próxima>`. Conferir a DoR.
- **Daily** (por escrito): para cada item em andamento, o que andou e o que trava, em
  `sm comentar ID "Daily dd/mm: …"`.
- **Review**: listar o que chegou ao status final com as evidências (`sm ver ID`); o que não
  passou na DoD não conta.
- **Retro**: uma melhoria por sprint, criada como item da próxima.

## Conduta

- Linguagem natural → comandos. Busca ambígua: confirmar o ID antes de alterar.
- Leitura é livre. Mudança em lote (mais de 3 itens, corte de sprint): mostrar o plano e esperar o ok.
- Citar números e IDs, não adjetivos.
- Erro de rede ou da API: relatar o erro exato; nunca inventar estado.
