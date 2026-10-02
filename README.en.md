# Espelho — interoperable process: the method as code, mirrored into four tools

Teams use different tools. When the process lives inside one of them, it does not cross over to
the others: each board becomes its own version of the rules. This repository treats the process
as code, outside any tool, and treats each tool as a showcase that receives the reflection of a
single source of truth. The method is operated by agentic systems through natural language.

The documentation is in Portuguese. This page is a summary.

## The thesis, in three rules

1. **One source of truth.** Items live in one tool; the others are mirrors. In stage 1 nothing
   flows back from a mirror.
2. **Identity lives in the item itself.** Every mirrored card carries its origin ID (an `op:ID`
   marker). Updates go by that ID, never by title and never by the syncer's local memory: if the
   response to a create call is lost, the marker on the card prevents a duplicate.
3. **The rules of the method are code, not habit.** An item without evidence cannot reach the
   final status; a column at its WIP limit refuses the next item; a sprint above capacity shows the
   excess. These rules apply to every tool alike, because they depend on none of them.

## Lineage

Nothing here is new as an idea. It is software engineering discipline applied to managing one's
own work: single source of truth, idempotent operations, acceptance criteria as a gate, separation
between whoever executes and whoever verifies. Scrum and Kanban provide the vocabulary.

## What is demonstrated (stage 1)

A real backlog of 71 items across six sprints was mirrored from OpenProject into Jira, Trello and
GitHub Projects. In each mirror, a second run changed nothing, no duplicate appeared even with the
network failing mid-load, and hours per sprint match the source. Each tool imposed a different
translation cost: Jira required story points to stand in for hours; Trello has no epics, sprints or
estimates and needed labels and title suffixes; GitHub Projects supported everything natively but
its API cannot create board views. None of the three, by default, enforces WIP or requires evidence
to close an item. Figures and failures found along the way: [RESULTADOS.md](RESULTADOS.md).

## What is not yet demonstrated (stage 2)

The way back: changes made in any mirror flowing to the source through the same rules. Every
mirror already stores a reference copy of each item, which is what makes it possible to tell
which side changed without trusting each tool's clock.

## Reproduce

Python 3 (tested on 3.13), no dependencies, no network, no accounts:

```bash
python3 -m unittest discover -s testes -v      # 12 tests, one per claim
bash testes/sabotagens.sh                      # 4 planted defects, all caught; 1 control
```

The usage measurement in RESULTADOS.md was taken on data that is not published. The `sm prova`
command is the same one: reproduce the method and produce your own number.

## License

Apache 2.0.
