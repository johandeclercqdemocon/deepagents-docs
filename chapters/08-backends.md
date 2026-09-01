# Chapter 8 — Backends

The filesystem tools are one interface with several implementations underneath. Choosing the
backend decides where files actually live — in graph state, on your disk, or in a database —
and it is the decision with the largest blast radius in this book, because one of the options
gives a language model write access to your machine.

## The options

```
['BackendProtocol', 'CompositeBackend', 'ContextHubBackend', 'FilesystemBackend',
 'LangSmithSandbox', 'LocalShellBackend', 'NamespaceFactory', 'StateBackend', 'StoreBackend']
```

The four that matter:

| Backend | Files live in | Survives | Use for |
|---|---|---|---|
| **`StateBackend`** (default) | LangGraph state | the thread | most things |
| **`FilesystemBackend`** | **your real disk** | forever | coding agents, local tools |
| **`StoreBackend`** | a LangGraph Store | across threads | long-term memory |
| **`CompositeBackend`** | routed by path | mixed | the realistic production shape |

## `StateBackend` — the default

Files are a dict in graph state (Chapter 4). Nothing touches your disk:

```
in state: ['/memo.md']
```

Right for almost everything. Scoped to the thread, checkpointed, inspectable, and completely
safe — the agent cannot reach anything you did not put there.

Its limit is size: every file is in every checkpoint.

## `FilesystemBackend` — real files, and a real risk

```python
FilesystemBackend(root_dir="/path/to/project")
```

The agent reads and writes **actual files**:

```
ls        -> ['/seed.txt']
read_file -> '1  on disk'
```

And writes land on disk:

```
FilesystemBackend(virtual_mode=False)   file on real disk? True  -> AGENT WROTE THIS
```

That is the point for a coding assistant, and it is a genuine hazard everywhere else. The
library's own docstring is blunt about it:

> **Security Warning.** This backend grants agents direct filesystem read/write access...
> Inappropriate use cases: [untrusted workloads without sandboxing].

### `virtual_mode` does not mean "virtual"

The trap, and the reason to read this section rather than skim it. The parameter defaults to
`True` and sounds like it keeps things in memory. Measured:

```
FilesystemBackend(root_dir=d, virtual_mode=True)
  file on real disk? True
  in state files?    False
```

**It still wrote to the disk.** From the docstring:

> `virtual_mode=True` is primarily for virtual path semantics... It can also provide
> path-based guardrails by blocking traversal (`..`, `~`) and absolute paths outside
> `root_dir`, but **it does not provide sandboxing or process isolation.**

So `virtual_mode` constrains *paths*, not *access*. It stops `../../etc/passwd`; it does not
stop the agent overwriting your source files inside `root_dir`.

> **If you want files that never touch your disk, use `StateBackend` — the default. Not
> `FilesystemBackend(virtual_mode=True)`.**

If you do use it: point `root_dir` at a scratch directory, pair it with human approval on
`write_file` and `delete` (Chapter 13), and treat it as you would `exec`.

## `StoreBackend` — memory across threads

Files in a LangGraph Store, so they outlive the thread:

```python
StoreBackend(namespace=lambda rt: ("memories",))

agent = create_deep_agent(model=model, backend=StoreBackend(namespace=ns), store=InMemoryStore())
```

Written on thread A, read on thread B:

```
thread B sees: ['/memo.md']
               1  remembered across threads
```

Two API details that will cost you time, both changed recently:

**`namespace` is a callable, not a tuple.** `StoreBackend(namespace=("memories",))` raises
`TypeError: 'tuple' object is not callable` — from deep inside the write, not at construction.
It takes the runtime, so the namespace can depend on the request:

```python
StoreBackend(namespace=lambda rt: ("memories", rt.context.user_id))
```

That is also how you get per-user memory, and Chapter 28 explains why the tenant must come
from context rather than anything the model supplies.

**Backend factories were removed in 0.7.** Widely-published examples — including the official
skill — show `backend=lambda rt: StoreBackend(rt)`. Against 0.7.11:

```
TypeError: backend must be an initialized backend instance. Backend factories were
removed in deepagents 0.7; pass StateBackend(), CompositeBackend(...), or another
BackendProtocol instance instead.
```

A good error message, at least. Pass an instance.

## `CompositeBackend` — the production shape

Route by path prefix:

```python
CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(namespace=lambda rt: ("memories", rt.context.user_id)),
        "/repo/": FilesystemBackend(root_dir="/srv/checkout"),
    },
)
```

Scratch work stays in state and disappears with the thread; anything under `/memories/`
persists across sessions; anything under `/repo/` is real. One filesystem to the agent, three
storage policies to you.

This is usually what a real deployment wants, and the routing is also a **security boundary**:
if only `/repo/` maps to disk, nothing the agent writes elsewhere can escape.

## Choosing

- Start with the **default**. Do not configure a backend until you need one.
- Files should survive across sessions → **`StoreBackend`**.
- The agent genuinely edits real files (a coding agent) → **`FilesystemBackend`**, scoped, with
  approval on writes.
- More than one of those → **`CompositeBackend`**.

And the rule worth repeating: **`virtual_mode=True` is not a sandbox.**

## Try it

Confirm the default keeps files off your disk:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel
m = ScriptedModel(script=[{'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/memo.md','content':'hi'}}]}, 'done'])
out = create_deep_agent(model=m).invoke({'messages':[{'role':'user','content':'go'}]})
print('in state:', sorted(out['files']))
"
```

Then watch `FilesystemBackend` write to a real directory **with `virtual_mode=True`** — the
finding worth seeing yourself:

```bash
uv run python -c "
import tempfile, pathlib
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from examples.scout.fakes import ScriptedModel

d = tempfile.mkdtemp()
m = ScriptedModel(script=[{'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/new.txt','content':'AGENT WROTE THIS'}}]}, 'done'])
create_deep_agent(model=m, backend=FilesystemBackend(root_dir=d, virtual_mode=True)).invoke(
    {'messages':[{'role':'user','content':'go'}]})
f = pathlib.Path(d) / 'new.txt'
print('on real disk:', f.exists(), '->', f.read_text().strip() if f.exists() else '')
"
```

And provoke the factory error, so you recognise it in a stale tutorial:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from examples.scout.fakes import ScriptedModel
try:
    create_deep_agent(model=ScriptedModel(script=['ok']), backend=lambda rt: StoreBackend(rt))
except TypeError as e:
    print('TypeError:', str(e)[:110])
"
```

## Takeaways

- The filesystem tools are one interface over several backends. **Start with the default
  `StateBackend`** — files in graph state, nothing on disk.
- **`FilesystemBackend` gives a language model read/write access to real files.** The
  library's own docstring calls it a security warning.
- **`virtual_mode=True` is not a sandbox.** It constrains paths — blocking `..` and escapes
  from `root_dir` — and **still writes to your disk**. For files that never touch disk, use
  `StateBackend`.
- `StoreBackend` gives memory across threads. **`namespace` is a callable, not a tuple**, and
  taking the runtime is how you scope memory per user.
- **Backend factories were removed in 0.7** — `backend=lambda rt: ...` now raises. Pass an
  instance. Most published examples are stale.
- `CompositeBackend` routes by path prefix and is the realistic production shape — and its
  routing table is a **security boundary**.

---

Previous: [Chapter 7 — The virtual filesystem](07-virtual-filesystem.md) ·
Next: [Chapter 9 — Subagents](09-subagents.md)
