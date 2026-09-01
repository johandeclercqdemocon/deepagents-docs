# Chapter 30 — Patterns

Six shapes cover most deep agent applications. Each is configuration you have already seen;
the value is knowing which one a problem wants.

## 1. The investigator

Read a lot, conclude briefly, write a report. `scout`.

```
seed workspace -> plan -> grep/read -> check tools -> write /findings.md
```

**Use when:** the input is documents and the output is a judgement.

**Cost:** turns proportional to the material. This is the archetype the harness was built for,
and the one where its overhead most clearly pays.

## 2. The producer

Write an artefact — a document, a migration, a set of files — refining as it goes.

**Use when:** the deliverable is the files, not the answer.

**Cost:** similar, plus the risk that it declares success without producing anything.
Chapter 26's first check — *did it produce the artefact at all* — matters most here.

**Needs:** a named output path, and `edit_file` rather than repeated `write_file`.

## 3. Orchestrator with specialists

A parent that plans and delegates; subagents that grind.

```
parent (large model) -> task -> [log-reader, config-checker] (small model)
```

**Use when:** subtasks produce a lot of context and small answers (Chapter 9).

**Cost:** a model call per delegation, each paying the full ~2,400-token tool block. Real
savings on bulky subtasks; a loss on small ones.

**The failure:** hierarchy for its own sake. One level is usually right; three means the design
got away from you.

## 4. The long conversation

An assistant with memory across sessions, files that persist, and a growing understanding of a
project.

```
CompositeBackend(default=StateBackend(), routes={"/memories/": StoreBackend(...)})
```

**Use when:** the same user returns and continuity is the value.

**Cost:** memory hygiene becomes a real job — contradictions, staleness, deletion
(Chapter 11), and injection that persists across sessions (Chapter 28).

## 5. The supervised operator

An agent that acts on the world, with approval before anything irreversible.

```
interrupt_on={"write_file": True, "delete": True} + checkpointer
```

**Use when:** the agent changes real things.

**Cost:** a human in the loop, which is a product problem before it is a technical one. Ask
rarely, send evidence, offer edit (Chapter 13).

## 6. The one-shot with files

Not really a deep agent: a single task where the input happens to be documents. Seed files,
let it read, take the answer.

**Use when:** you want the filesystem's context handling without long-running behaviour.

**Cost:** the fixed ~2,400 tokens. Worth it if the documents are large; otherwise use
`create_agent`.

## Choosing

| Signal | Pattern |
|---|---|
| A few turns, no documents | **not a deep agent** — `create_agent` |
| Large documents, one answer | One-shot with files |
| Documents in, judgement out | Investigator |
| Files are the deliverable | Producer |
| Bulky independent subtasks | Orchestrator with specialists |
| Continuity across sessions | Long conversation |
| Changes real things | Supervised operator |
| Control flow you define | **LangGraph** (Chapter 31) |

Read top to bottom, stop at the first match. The order is by cost and predictability.

Patterns compose: a supervised investigator with specialists and memory is a normal design,
and it is also four capabilities to debug at once — add them one at a time, and add each only
when you can name what it fixed.

## Two anti-shapes worth naming

**The agent that could have been a chain.** If the steps are known — retrieve, summarise,
write — that is a chain in LangChain. You are paying for a model to rediscover a sequence you
already know.

**The hierarchy.** Agents delegating to agents delegating to agents. Every level is a model
call, context is lost at each boundary, and debugging spans several transcripts none of which
contains the whole story.

## Try it

Compare an investigator with a plain agent on the same question:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langchain.agents import create_agent
from examples.scout.fakes import ScriptedModel

deep = ScriptedModel(script=['done']); plain = ScriptedModel(script=['done'])
create_deep_agent(model=deep).invoke({'messages':[{'role':'user','content':'hi'}]})
create_agent(plain, tools=[]).invoke({'messages':[{'role':'user','content':'hi'}]})
print('deep agent tools :', len(deep.bound_tools), deep.bound_tools)
print('plain agent tools:', len(plain.bound_tools), plain.bound_tools or 'none')
"
```

Eight tools versus none. On a task with no documents, that is pure overhead; on one with
four log files, it is the reason the run finishes.

## Takeaways

- Six shapes: **investigator**, **producer**, **orchestrator with specialists**, **long
  conversation**, **supervised operator**, **one-shot with files**.
- Choose the first match in the cost-ordered list, not the most interesting one.
- The investigator is the archetype — documents in, judgement out — and where the harness's
  overhead most clearly pays.
- For the producer, the critical check is **did it produce the artefact at all**.
- Delegation pays on **bulky** subtasks and loses on small ones. **One level of hierarchy is
  usually right; three means the design got away from you.**
- Continuity across sessions makes memory hygiene a real job, including persistent injection.
- Patterns compose, but add capabilities one at a time and only when you can name what each
  fixed.
- Two anti-shapes: **the agent that should have been a chain**, and **the hierarchy**.

---

Previous: [Chapter 29 — Deployment](29-deployment.md) ·
Next: [Chapter 31 — Deep Agents, LangChain and LangGraph](31-the-stack.md)
