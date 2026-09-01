# Chapter 11 — Memory across sessions

Three kinds of memory, three lifetimes. Most confusion about deep agents is a mix-up between
them.

| Memory | Scope | Survives | Mechanism |
|---|---|---|---|
| **Messages** | one thread | the thread | the conversation |
| **Files** | one thread | the thread | `StateBackend` (default) |
| **Long-term** | whatever you choose | forever | `StoreBackend` |

Chapter 4 covered the first two. This chapter is the third: facts that outlive the
investigation.

## Files that cross threads

`StoreBackend` puts the filesystem in a LangGraph Store instead of graph state:

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model=model,
    backend=StoreBackend(namespace=lambda rt: ("memories",)),
    store=InMemoryStore(),
    checkpointer=InMemorySaver(),
)
```

Written on one thread, read on a completely different one:

```
thread B sees: ['/memo.md']
               1  remembered across threads
```

Same tools — `write_file`, `read_file`, `ls`. The agent does not know or care that these
files outlive the conversation. **Long-term memory is just a filesystem with a longer
lifetime**, which is a genuinely elegant piece of design: nothing new to learn.

## The namespace is the scope

```python
StoreBackend(namespace=lambda rt: ("memories", rt.context.user_id))
```

It is a **callable** taking the runtime (Chapter 8), which is what lets scope depend on the
request. That makes it the access-control boundary:

- `("memories",)` — one shared memory for everyone.
- `("memories", user_id)` — per user.
- `("memories", org_id, user_id)` — per user within an organisation.

Two rules, and Chapter 28 explains why they matter:

**Take the scope from context, never from state or a tool argument.** Context is set by your
application; state can be influenced by model output and user input. A namespace built from
state is a path traversal waiting to happen.

**Put the tenant in the namespace tuple, not in the filename.** `("memories", user)` is
enforceable; `("memories",)` with files called `alice-notes.md` is one prefix bug from a leak.

## What to remember

The hard part is not the API. An agent that writes everything to memory becomes slow,
expensive and self-contradictory.

Worth remembering:

- **Stated preferences.** "Always cite the runbook." "Reply in Dutch."
- **Stable facts.** Which cluster this team owns; the on-call rota's shape.
- **Reusable outcomes.** "node-3 has had three disk incidents; log retention is never
  applied." That makes the next investigation start warmer, which is the whole promise.

Not worth remembering:

- **Anything derivable.** If it is in your database, read your database. A copy drifts.
- **Whole transcripts.** That is what the thread is for.
- **The agent's speculation.** This is the damaging one: an agent that writes guesses to
  long-term memory reads them back later as established fact, and the error compounds
  invisibly across sessions.

The design rule that follows:

> **Prefer writing memory from deterministic code.** Where the agent writes it, constrain the
> shape and treat what it wrote as a claim, not a fact.

A practical middle ground: have the agent propose memory in a file the *parent* code reviews
before promoting it to the long-term namespace.

## Forgetting

Memory that only grows is a liability — for contradictions, for cost, and for privacy law.
Decide three things before you ship:

**Deletion.** A user asking to be forgotten must be satisfiable, which means being able to
enumerate every namespace holding their data. `("memories", user_id)` makes that one call;
a shared namespace with prefixed filenames makes it a scan. Design for it on day one.

**Updating rather than appending.** Preferences change. Overwrite `/prefs.md` rather than
appending a list of every preference ever expressed, or the agent reads contradictory
instructions and picks arbitrarily.

**Staleness.** Facts expire. Files carry `created_at` and `modified_at` (Chapter 4) — put a
date in the content too, so the agent can judge for itself.

## `CompositeBackend` is how you get both

You rarely want *everything* persistent. Scratch work should die with the thread; conclusions
should not. Route by path (Chapter 8):

```python
CompositeBackend(
    default=StateBackend(),                                             # /scratch/, /logs/
    routes={"/memories/": StoreBackend(namespace=lambda rt: ("memories", rt.context.user_id))},
)
```

Now `/memories/preferences.md` persists and everything else is ephemeral — and you can tell
the agent so in its system prompt: *"Anything under /memories/ will be there next time.
Nothing else will."*

That sentence is worth including. Without it the agent has no way to know which of its files
are durable, and will either lose work or clutter your store.

## Try it

Watch a file cross a thread boundary:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver
from examples.scout.fakes import ScriptedModel

store = InMemoryStore()
ns = lambda rt: ('memories',)

def run(script, tid):
    a = create_deep_agent(model=ScriptedModel(script=script), backend=StoreBackend(namespace=ns),
                          store=store, checkpointer=InMemorySaver())
    return a.invoke({'messages':[{'role':'user','content':'go'}]}, {'configurable':{'thread_id':tid}})

run([{'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/memo.md','content':'remembered across threads'}}]}, 'done'], 'A')
out = run([{'text':'y','tool_calls':[{'name':'read_file','args':{'file_path':'/memo.md'}}]}, 'done'], 'B-totally-different')
print([str(m.content) for m in out['messages'] if type(m).__name__=='ToolMessage'])
print('store keys:', [i.key for i in store.search(('memories',))])
"
```

Then change `ns` to `lambda rt: ('memories', 'someone-else')` for the second run and watch the
memory disappear — that is the namespace doing its job.

## Takeaways

- Three memories: **messages** (the thread), **files** (the thread), **long-term** (as long as
  you keep it).
- `StoreBackend` makes the filesystem outlive the thread. Same tools — **long-term memory is
  just a filesystem with a longer lifetime.**
- **The namespace callable is the scope and the access-control boundary.** Take it from
  context, never from state; put the tenant in the tuple, not the filename.
- Remember stated preferences, stable facts and reusable outcomes. Never anything derivable,
  whole transcripts, or **the agent's own speculation** — which it will later read as fact.
- **Prefer writing memory from deterministic code**; treat agent-written memory as a claim.
- Plan deletion, in-place updates and staleness before shipping.
- `CompositeBackend` gives ephemeral scratch and durable conclusions — and **tell the agent in
  its prompt which paths survive.**

---

Previous: [Chapter 10 — Skills](10-skills.md) ·
Next: [Chapter 12 — Prompting a deep agent](12-prompting.md)
