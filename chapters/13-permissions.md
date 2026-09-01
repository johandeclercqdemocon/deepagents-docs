# Chapter 13 — Permissions and approval

A deep agent can write and delete files. With `FilesystemBackend` those are real files
(Chapter 8). This chapter is about putting a human, or a rule, between the model and anything
you cannot undo.

## Approval in one argument

```python
agent = create_deep_agent(
    model=model,
    interrupt_on={"write_file": True},
    checkpointer=InMemorySaver(),      # required for the resume
)
```

The run stops **before** the tool executes:

```
interrupted: True
file written yet: False
next: ('HumanInTheLoopMiddleware.after_model',)
```

The file has not been written. Approve, and it is:

```python
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
```

```
after approve, file: True
```

That is LangGraph's `interrupt()` underneath (Chapter 5), so everything from that layer
applies: the run does not block a thread, it **stops and persists**, and the approval can
arrive minutes later from another process.

## The failure that only appears at the resume

Worth knowing precisely, because it is not the failure you would guess. Without a
checkpointer:

```
built and ran; interrupted: True | file: False
```

Identical to the working case. It pauses, nothing complains, and the write is correctly
blocked. The difference appears one request later:

```
RuntimeError: Cannot use Command(resume=...) without checkpointer
```

**A missing checkpointer does not break the pause — it breaks the resume**, in a different
part of your code. Test the whole cycle, not just "does it stop?".

## What to gate

Gating everything trains the reviewer to approve without reading, and a rubber stamp approves
the one bad action too. Gate the irreversible and the expensive:

| Tool | Gate it when |
|---|---|
| `write_file` | with `FilesystemBackend` — it overwrites real files |
| `delete` | almost always |
| `edit_file` | with `FilesystemBackend` |
| your own tools | anything that sends, spends, or deletes |
| `read_file`, `grep`, `ls`, `glob` | essentially never — they are reads |

With the default `StateBackend`, `write_file` touches only graph state, and gating it is
usually unnecessary. **The backend decides how dangerous the filesystem tools are** — which is
why Chapters 8 and 13 are read together.

## Decisions beyond yes

```python
Command(resume={"decisions": [{"type": "approve"}]})
Command(resume={"decisions": [{"type": "reject", "message": "Do not touch that path."}]})
Command(resume={"decisions": [{"type": "edit", "args": {"file_path": "/safe/out.md"}}]})
```

The **edit** path matters most and is the one people skip. An agent about to write to the
wrong path can be corrected rather than rejected — rejection throws away everything it did to
get there. Exact shapes vary by version; check yours.

## Blocking without a human

If the answer is always no, an approval queue nobody staffs is worse than a rule. Middleware
can refuse outright (Chapter 14):

```python
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

@wrap_tool_call
def protect(request, handler):
    if request.tool_call["name"] == "delete":
        return ToolMessage(content="Refused: deletion is not permitted.",
                           tool_call_id=request.tool_call["id"])
    return handler(request)
```

Return a **`ToolMessage`**, not a string — a bare string becomes a `HumanMessage`, so the
refusal reads to the model as the *user* saying it.

The agent sees a normal tool result and carries on. This is a far stronger control than
asking it not to, in the prompt.

## Path rules are better than tool rules

Often the question is not *which tool* but *which path*. A rule beats a human for that:

```python
@wrap_tool_call
def protect_paths(request, handler):
    path = request.tool_call["args"].get("file_path", "")
    if request.tool_call["name"] in {"write_file", "edit_file", "delete"} \
       and not path.startswith("/scratch/"):
        return ToolMessage(content=f"Refused: writes are only allowed under /scratch/. Got {path}.",
                           tool_call_id=request.tool_call["id"])
    return handler(request)
```

Note the refusal *says why and where is allowed* — so the model can correct itself rather than
retrying the same call. Tool output is prompt (Chapter 3).

`CompositeBackend` routing (Chapter 8) does this structurally, which is stronger still: if
only `/repo/` maps to disk, nothing written elsewhere can escape regardless of what any rule
forgets.

## In a web application

1. `POST /investigate` → `invoke(...)`. If the result has `__interrupt__`, store the
   `thread_id` against a review task and return "pending approval".
2. The reviewer's UI renders the pending action.
3. `POST /approve/{thread_id}` → `invoke(Command(resume=...), config)`.

Nothing is held open between steps. Two operational notes: the checkpointer must be **shared
across workers** (Postgres, not memory), and step 3 must be idempotent because a reviewer will
double-click.

And decide what happens to a request nobody answers. Paused threads sit forever.

## Try it

Watch the write get blocked, then approved:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from examples.scout.fakes import ScriptedModel

W = {'text':'writing','tool_calls':[{'name':'write_file','args':{'file_path':'/out.md','content':'x'}}]}
a = create_deep_agent(model=ScriptedModel(script=[W,'done']),
                      interrupt_on={'write_file': True}, checkpointer=InMemorySaver())
cfg = {'configurable': {'thread_id': 't'}}
out = a.invoke({'messages':[{'role':'user','content':'go'}]}, cfg)
print('paused        :', '__interrupt__' in out)
print('file written  :', '/out.md' in out.get('files', {}))
final = a.invoke(Command(resume={'decisions':[{'type':'approve'}]}), cfg)
print('after approve :', '/out.md' in final.get('files', {}))
"
```

Then drop the checkpointer and confirm the asymmetry — it still pauses, and only the resume
fails:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langgraph.types import Command
from examples.scout.fakes import ScriptedModel
W = {'text':'writing','tool_calls':[{'name':'write_file','args':{'file_path':'/out.md','content':'x'}}]}
b = create_deep_agent(model=ScriptedModel(script=[W,'done']), interrupt_on={'write_file': True})
out = b.invoke({'messages':[{'role':'user','content':'go'}]})
print('still pauses:', '__interrupt__' in out)
try:
    b.invoke(Command(resume={'decisions':[{'type':'approve'}]}))
except RuntimeError as e:
    print('resume ->', e)
"
```

## Takeaways

- `interrupt_on={"tool": True}` pauses **before** the tool runs. It is LangGraph's
  `interrupt()`, so the run stops and persists rather than blocking.
- **Without a checkpointer it still pauses and still blocks the write** — the failure is
  deferred to the resume, one request later. Test the whole cycle.
- Gate the **irreversible and expensive**, never reads. **The backend decides how dangerous
  the filesystem tools are** — with `StateBackend`, `write_file` touches only state.
- Support **edit**, not just approve and reject; rejection discards all the work.
- If the answer is always no, **block in middleware** rather than queueing a human — and
  return a `ToolMessage`, not a string.
- **Path rules often beat tool rules**, and refusals should say what *is* allowed so the model
  can correct itself. `CompositeBackend` routing enforces this structurally.
- In a web app: pause, store the thread id, resume later. Shared checkpointer, idempotent
  approve, and a policy for requests nobody answers.

---

Previous: [Chapter 12 — Prompting a deep agent](12-prompting.md) ·
Next: [Chapter 14 — Middleware and custom tools](14-middleware-and-tools.md)
