# Chapter 22 — Observing a long run

A deep agent runs for minutes. Waiting for the final message and hoping is not an operational
strategy — and unlike a chain, this one has three separate things worth watching.

## Three signals, not one

| Signal | Answers | Where |
|---|---|---|
| **Messages** | what is it doing right now | the stream |
| **Todos** | where does it think it is | state |
| **Files** | what has it actually produced | state |

Most people watch only the first. **The second is the best stuck-detector and the third is the
deliverable.**

## Streaming

It is a LangGraph graph (Chapter 5), so the stream modes are LangGraph's:

```python
for chunk in agent.stream(payload, stream_mode="updates"):
    print(chunk)
```

- **`updates`** — what each node returned. The right default for "which step is it on".
- **`values`** — the whole state after each step, so you can watch `todos` and `files` evolve.
- **`messages`** — token by token, for a UI.

Two warnings inherited from the layers below.

**`stream_mode="messages"` includes tool output.** A UI rendering every chunk will print raw
file contents into the conversation. Filter on `metadata["langgraph_node"]`.

**Subagent work is invisible by default.** Pass `subgraphs=True` to see inside — otherwise a
subagent is one opaque step, which is exactly the debugging problem from Chapter 9.

```python
for ns, chunk in agent.stream(payload, stream_mode="updates", subgraphs=True):
    print(ns or "parent", chunk)
```

## Watching the plan

The cheapest progress indicator available:

```python
for chunk in agent.stream(payload, stream_mode="values"):
    todos = chunk.get("todos", [])
    done = sum(1 for t in todos if t["status"] == "completed")
    print(f"{done}/{len(todos)} complete")
```

Two things you can act on. **Progress**, for a UI or a log. And **stuck-ness**: a plan
unchanged over many turns means the agent is going round, and you can stop it before the
recursion limit does (Chapter 21).

This is worth wiring up early. It is a handful of lines and it is the difference between a
long-running agent being opaque and being legible.

## Inspecting a run afterwards

With a checkpointer, the whole history is queryable:

```python
snapshot = agent.get_state(config)
snapshot.values["files"]                 # what exists now
snapshot.values.get("todos")
snapshot.next                            # empty = finished; non-empty = paused
snapshot.interrupts                      # waiting for approval?

for h in agent.get_state_history(config):
    print(h.metadata.get("step"), sorted(h.values.get("files", {})))
```

That last loop is genuinely useful in a way it is not for a short agent: it shows **when each
file appeared**. "The report was written at step 4, before the config was read" is a finding
you cannot get from the final state.

## What to log in production

If you adopt nothing else:

- **The `thread_id` on every line.** Without it you cannot reconstruct a run.
- **Every tool call and result summary** — name, arguments, and whether the result contained
  `Error`. This is the record you will want when someone asks what the agent changed.
- **Turn count and tokens** (Chapter 21).
- **The final `files` keys**, so you know what it produced.

Tracing via LangSmith works unchanged — it is instrumented at the LangChain layer, so set
`LANGSMITH_TRACING=true` and you get the tree, including subagents, with no code change. Note
the variables are `LANGSMITH_*`; the older `LANGCHAIN_*` names no longer work.

## What to alert on

- **`GraphRecursionError` count** — should be zero.
- **p99 turns per run** — runaways hide in the tail.
- **Tool error rate**, especially filesystem errors. A rising rate usually means paths changed
  under the agent.
- **Interrupt age**, if you use approval (Chapter 13). A review request nobody answers is an
  invisible failure.
- **Runs producing no files.** For a file-producing agent, an empty `files` is a failed run
  regardless of what the final message says.

That last one is specific to this layer and worth adding: it catches confident narration over
a broken filesystem, which Chapter 18 warned is the characteristic failure here.

## Try it

Watch the plan advance:

```bash
uv run python -c "
from examples.scout.agent import build
from examples.scout.workspace import seed

for chunk in build().stream({'messages':[{'role':'user','content':'why did node-3 fail?'}], 'files': seed()},
                            stream_mode='values'):
    todos = chunk.get('todos', [])
    if todos:
        done = sum(1 for t in todos if t['status'] == 'completed')
        print(f'{done}/{len(todos)} complete  files={len(chunk.get(\"files\", {}))}')
"
```

Then see which step produced the report:

```bash
uv run python -c "
from langgraph.checkpoint.memory import InMemorySaver
from examples.scout.agent import build
from examples.scout.workspace import seed

agent = build(checkpointer=InMemorySaver())
cfg = {'configurable': {'thread_id': 'run-1'}}
agent.invoke({'messages':[{'role':'user','content':'why did node-3 fail?'}], 'files': seed()}, cfg)
for h in reversed(list(agent.get_state_history(cfg))):
    files = sorted(h.values.get('files', {}))
    print(f\"step {str(h.metadata.get('step')):>3}  {len(files)} files  findings={'/findings.md' in files}\")
"
```

## Takeaways

- Watch **three** signals: messages (what now), **todos (where it thinks it is)**, files (what
  it produced). Most people watch only the first.
- Stream modes are LangGraph's. `updates` for steps, `values` to watch todos and files evolve.
- **`stream_mode="messages"` includes tool output** — filter on `langgraph_node`.
- **Subagent work is invisible unless you pass `subgraphs=True`.**
- A **todo list unchanged over many turns** is the cheapest stuck-detector, and lets you stop a
  run before the recursion limit does.
- `get_state_history` shows **when each file appeared**, which the final state cannot.
- Log the `thread_id`, every tool call and whether it errored, turns and tokens, and the final
  file list. LangSmith works unchanged with `LANGSMITH_*` variables.
- Alert on recursion errors, p99 turns, tool error rate, interrupt age — and **runs that
  produced no files**, which catches confident narration over a broken filesystem.

---

Previous: [Chapter 21 — Runaway agents and cost](21-runaway-and-cost.md) ·
Next: [Chapter 23 — Cookbook](23-cookbook.md)
