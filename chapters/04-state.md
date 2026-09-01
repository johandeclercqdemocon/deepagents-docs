# Chapter 4 — State: files and messages

A deep agent has two kinds of memory, and keeping them straight explains most of what the
harness is for.

**`messages`** — the conversation. Everything said, every tool call, every tool result. Grows
without bound and is re-sent on every model call.

**`files`** — the virtual filesystem. Written and read deliberately, and **not** re-sent
unless the agent reads a file.

That distinction is the whole idea:

> **The message list is what the agent has *said*. The filesystem is what it has *done*.**

## What a file actually is

```python
result["files"]["/a.md"]
```

```json
{
  "content": "hello",
  "encoding": "utf-8",
  "created_at": "2026-09-01T13:31:10.738274+00:00",
  "modified_at": "2026-09-01T13:31:10.738274+00:00"
}
```

A dict keyed by **absolute path**, with content and timestamps. Not a real file — by default
nothing touches your disk. `write_file("notes.md", ...)` stores `/notes.md`; paths are
normalised to absolute.

This is ordinary LangGraph state, which means it is checkpointed, inspectable, and passable as
input — that last one is how `scout` gets its logs (Chapter 7).

## Why this fixes the context problem

Compare two ways of reading four log files.

**Without a filesystem**, each result stays in the message list. Turn five re-sends all four
logs. Cost grows with the square of the work, and eventually the context window ends the run.

**With one**, the agent greps to find the relevant file, reads *part* of it, writes a
conclusion to `/findings.md`, and moves on. The transcript holds the conclusion; the evidence
stays in the filesystem.

The agent can always re-read a file. It just does not have to carry it.

This is why `read_file` takes `offset` and `limit`, and why `grep` returns paths rather than
lines (Chapter 3) — every design decision points at keeping bulk out of the context.

## Files do not persist by themselves

The trap, measured:

```
run1 files: ['/a.md'] | run2 files: []
```

Two `invoke` calls on the same agent object. The second starts with an **empty** filesystem —
the first run's work is gone. State lives in the checkpointer, and with no checkpointer each
invocation is independent.

Add one, and a `thread_id`:

```python
agent = create_deep_agent(model=model, checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "incident-4471"}}
```

```
files on thread: ['/a.md']
ls saw: ['/a.md']
```

The second run sees the first run's file, and `ls` finds it.

Both of those are LangGraph concepts (Chapter 5). The rule to carry:

> **A long-running investigation needs a checkpointer and a stable `thread_id`.** Without
> them the filesystem is scratch space for one invocation.

For memory across *different* threads — facts that outlive one investigation — see
Chapter 11.

## Reading and seeding state

You can pass `files` in as input, which is how the example provides its logs:

```python
agent.invoke({
    "messages": [{"role": "user", "content": "why did node-3 fail?"}],
    "files": seed(),          # {"/logs/api.log": create_file_data("...")}
})
```

`create_file_data` from `deepagents.backends.utils` builds the dict shape above. Seeding is
useful well beyond examples — attaching an uploaded document, or handing the agent the output
of an earlier job.

And you can read state back:

```python
result["files"]["/findings.md"]["content"]
```

For `scout` that report is the deliverable. **The final message is a summary; the file is the
work.** Chapter 22 makes that a debugging habit.

## The state grows

Enabling capabilities adds keys:

| Key | Added by |
|---|---|
| `messages` | always |
| `files` | always |
| `todos` | `TodoListMiddleware` (Chapter 6) |

You can add your own with `state_schema`, and Chapter 14 covers when that is worth it. Mostly
it is not — a file is usually the better place for anything the agent produces, because a file
has a name the agent can reason about.

## Try it

Watch files vanish, then persist:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel
from langgraph.checkpoint.memory import InMemorySaver

def writer():
    return ScriptedModel(script=[
        {'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/a.md','content':'1'}}]},
        'done'])

a = create_deep_agent(model=writer())
print('no checkpointer, run 1:', sorted(a.invoke({'messages':[{'role':'user','content':'go'}]})['files']))
print('no checkpointer, run 2:', sorted(a.invoke({'messages':[{'role':'user','content':'go'}]})['files']))

b = create_deep_agent(model=writer(), checkpointer=InMemorySaver())
cfg = {'configurable': {'thread_id': 't'}}
b.invoke({'messages':[{'role':'user','content':'go'}]}, cfg)
print('checkpointer,   run 2:', sorted(b.invoke({'messages':[{'role':'user','content':'again'}]}, cfg)['files']))
"
```

Then look at the deliverable rather than the chat:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
print('final message:', out['messages'][-1].content)
print()
print('the actual work product:')
print(out['files']['/findings.md']['content'])
"
```

## Takeaways

- Two memories: **`messages` is what the agent said, `files` is what it did.**
- A file is a dict of content and timestamps, keyed by **absolute path**. Nothing touches your
  disk by default.
- The filesystem exists to keep bulk **out of the context window** — which is why `grep`
  returns paths and `read_file` takes `offset`/`limit`.
- **Files do not persist between invocations without a checkpointer.** Measured: the second
  run starts empty.
- A long investigation needs a **checkpointer and a stable `thread_id`** — both LangGraph
  concepts.
- You can **seed `files` as input**, which is how documents get to the agent.
- Read the deliverable out of `result["files"]`. The final message is a summary; the file is
  the work.

---

Previous: [Chapter 3 — The built-in tools](03-built-in-tools.md) ·
Next: [Chapter 5 — It is a LangGraph graph](05-it-is-a-graph.md)
