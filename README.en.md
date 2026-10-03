# Espelho Backlog

The work process as code, outside any tool: the tool goes back to being a means. One of them
holds the source of truth, and the others receive its reflection, each serving as a showcase for
an audience. The method is operated by agentic systems through natural language: whoever works
talks, the system applies the rules, and the boards are for whoever needs to follow the work.

The documentation is in Portuguese. This page is a summary.

## The problem

A management tool tends to stop being a means and become an end. The process becomes whatever
the tool can be configured to do, the work includes keeping the board up to date, and changing
tools means rebuilding the process. The method's rules (Definition of Ready, Definition of Done,
WIP limit, capacity) come to depend on how each tool was configured. None of the tools tested,
in their default configuration, prevents an item from being closed without evidence or a column
from exceeding its WIP limit.

Audiences, on the other hand, are many: different levels within the team and, above all,
clients, each with its own way of following the work. The board should be each audience's
showcase, not the place where the process lives.

## Principles

**One source of truth.** Items live in one tool; the others are mirrors, and nothing flows back
from a mirror to the source. Each mirror declares its own scope, so a client's board receives
only that client's project.

**Identity lives in the item itself.** Every mirrored card carries its origin ID. An item is
never recognized by its title, and nothing duplicates, even when the response to a create call
is lost. Single exception: Trello has no epics, so an epic becomes a label found by its name.

**The rules are code, not habit.** An item without evidence cannot reach the final status; a
column at its WIP limit refuses the next item; a sprint above capacity shows the excess. The
rules hold for any tool, because they depend on none. The Definition of Ready is applied by the
skill, in conversation, not by code.

**A planted defect before trust.** Every rule has a test, and every test is proven by a
sabotage: the defect is planted on purpose, and the test must fail. The sabotage script itself
checks that no test is left unbroken by at least one of them.

## Lineage

Nothing here is new as an idea. It is software engineering discipline applied to managing one's
own work: single source of truth, idempotent operations, acceptance criteria as a gate,
separation between whoever executes and whoever verifies. Scrum and Kanban provide the
vocabulary. AI-assisted development is taking up part of this discipline today, under names such
as spec-driven development. The code only makes the rules verifiable: a rule is checked at the
moment of the change, not remembered later, at review.

## Results

A backlog of 71 items across six sprints, mirrored from OpenProject into Jira, Trello and GitHub
Projects:

- **Fidelity:** all 71 items in the three mirrors (in Trello, the 11 epics as labels), with
  hours per sprint matching the source.
- **Idempotency:** a second execution changed nothing in any of the three.
- **Duplicates:** zero.
- **Usage:** from 2026-09-28 to 2026-10-02, all 20 changes recorded in the source were made
  through conversation, none through the tool's screen. The same measurement records no sprint
  progress in that period.

Before publication: successive rounds of independent audit, 49 tests and 49 planted defects, all
caught, with every test broken by at least one of them. Figures, each tool's translation cost
and the failures found: [RESULTADOS.md](RESULTADOS.md).

## Current limitation

Mirroring is one-way: changes made in a mirror do not yet flow back to the source. The basis for
the reverse path is in place: every mirror keeps a reference copy of each item, which makes it
possible to tell which side changed without relying on each tool's clock.

## Reproduce

Python 3 (tested on 3.13), no dependencies, no network, no accounts:

```bash
python3 -m unittest discover -s testes -v      # 49 tests
bash testes/sabotagens.sh                      # 49 planted defects, all detected; 1 control
```

The usage measurement in RESULTADOS.md was taken on data that is not published. The `sm prova`
command is the same one: reproduce the method and produce your own number.

## License

Apache 2.0.
