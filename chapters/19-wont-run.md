# Chapter 19 — When it won't run

Layer 1. The agent fails immediately, or a capability you configured is not there. These are
the friendly failures — cheap to reproduce and mostly deterministic.

Every message here came from an actual run.

## It raises

**A string instead of a dict:**

```python
agent.invoke("hello")
```

```
InvalidUpdateError: Expected dict, got hello
```

Agents take `{"messages": [...]}`. The error comes from LangGraph, two layers down
(Chapter 5) — which is why searching the Deep Agents documentation for it finds nothing.

**Reading the result as a message:**

```python
agent.invoke({...}).content
```

```
AttributeError: 'dict' object has no attribute 'content'
```

The result is a dict: `result["messages"][-1].content`.

**A backend factory:**

```python
create_deep_agent(model=model, backend=lambda rt: StoreBackend(rt))
```

```
TypeError: backend must be an initialized backend instance. Backend factories were
removed in deepagents 0.7; pass StateBackend(), CompositeBackend(...), or another
BackendProtocol instance instead.
```

Chapter 8. Most published examples still show the factory form.

**A `StoreBackend` namespace that is a tuple:**

```
TypeError: 'tuple' object is not callable
```

Raised deep inside the *write*, not at construction, so the traceback points at
`store.py` rather than your configuration. `namespace` takes a callable.

**Resuming without a checkpointer:**

```
RuntimeError: Cannot use Command(resume=...) without checkpointer
```

Chapter 13 — and note the pause worked.

## It runs, but the capability is missing

More common and much more expensive, because nothing tells you.

**No planning.**

```
default              ['ls', 'read_file', 'write_file', 'edit_file', 'delete', 'glob', 'grep', 'task']
+ TodoListMiddleware [..., 'write_todos']
```

`write_todos` is absent unless you add `TodoListMiddleware`. The agent works and never plans.

**No skills.**

```python
create_deep_agent(model=model, skills=["./skills/"])     # builds fine
```

Without a backend that can read them, this does nothing — no error, no warning, and the skill
never appears in the system prompt. Check by looking for the skill's name in the prompt
(Chapter 10).

**No files across runs.**

```
run1 files: ['/a.md'] | run2 files: []
```

No checkpointer, so each `invoke` starts empty (Chapter 4).

**No argument descriptions.**

```python
my_tool.args    # {'query': {'title': 'Query', 'type': 'string'}}   <- no description
```

`@tool` without `parse_docstring=True`.

All four are silent. **When a capability seems absent, verify it is present** rather than
debugging the model's behaviour.

## Deprecations worth reading

```python
create_deep_agent()      # no model
```

```
LangChainDeprecationWarning: Passing `model=None` to `create_deep_agent` is deprecated
and will be removed in deepagents==1.0.0.
```

It works today and will not. Pass a model explicitly — Chapter 17 says construct it in one
place anyway. Do not suppress deprecation warnings in this ecosystem; they are the earliest
signal that something you rely on is moving.

## Failures that come back as tool results

**An unknown subagent:**

```
We cannot invoke subagent nope because ...
```

Returned as a `ToolMessage`, not raised. The agent sees it and carries on, usually by doing
the work itself — so a typo'd `subagent_type` presents as "delegation isn't helping", not as
an error.

**Filesystem errors** (Chapter 3): missing file, no match for `edit_file`, `ls` without a
path. All returned.

This is the right default and it means **a broken configuration can run to completion**.
Chapter 18's error scan is the antidote.

## A checklist

1. Read the **last frame in your own file** and the exception.
2. If it mentions `InvalidUpdateError`, `GraphRecursionError` or checkpointers, you are in
   **LangGraph** — search there.
3. If a capability seems missing, **check `bound_tools` and the system prompt** before
   blaming the model.
4. If there is no error at all, **scan `ToolMessage`s for `Error`**.
5. Check the deprecation warnings you have been ignoring.

## Try it

Collect the raising failures so they are familiar:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from examples.scout.fakes import ScriptedModel

def show(label, fn):
    try: print(f'{label:26} -> OK')
    except Exception: pass
    try:
        fn(); print(f'{label:26} -> OK')
    except Exception as e:
        print(f'{label:26} -> {type(e).__name__}: {str(e).splitlines()[0][:58]}')

m = lambda: ScriptedModel(script=['ok'])
show('string input', lambda: create_deep_agent(model=m()).invoke('hello'))
show('result .content', lambda: create_deep_agent(model=m()).invoke({'messages':[{'role':'user','content':'h'}]}).content)
show('backend factory', lambda: create_deep_agent(model=m(), backend=lambda rt: StoreBackend(rt)))
" 2>&1 | grep -v '^ *$'
```

Then confirm the silent one — a skill configured with no backend:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel

seen = {}
class Spy(ScriptedModel):
    def _generate(self, messages, *a, **k):
        seen.setdefault('m', messages); return super()._generate(messages, *a, **k)
def text(msg):
    c = msg.content
    return c if isinstance(c, str) else ''.join(b.get('text','') for b in c if isinstance(b, dict))

create_deep_agent(model=Spy(script=['ok']), skills=['./skills/']).invoke(
    {'messages':[{'role':'user','content':'hi'}]})
prompt = chr(10).join(text(m) for m in seen['m'])
print('built without error, and skill in prompt:', 'incident-report' in prompt)
"
```

Built fine. Skill absent. No warning.

## Takeaways

- Raising failures: **string input** (`InvalidUpdateError`), **`.content` on the result**,
  **backend factories** (removed in 0.7), **a tuple `namespace`**, and **resume without a
  checkpointer**.
- Errors mentioning `InvalidUpdateError`, `GraphRecursionError` or checkpointers are
  **LangGraph's** — search there, not in Deep Agents docs.
- **Four capabilities fail silently**: planning without `TodoListMiddleware`, skills without a
  backend, files without a checkpointer, tool descriptions without `parse_docstring=True`.
- **Verify a capability is present** before debugging the model's behaviour around it.
- `create_deep_agent()` with no model is deprecated and will break at 1.0. Read deprecation
  warnings in this ecosystem.
- An unknown `subagent_type` is returned as a tool result, so it looks like "delegation isn't
  helping" rather than an error.
- No error does not mean no failure — **scan `ToolMessage`s for `Error`**.

---

Previous: [Chapter 18 — The debugging mindset](18-debugging-mindset.md) ·
Next: [Chapter 20 — When the agent does the wrong thing](20-wrong-thing.md)
