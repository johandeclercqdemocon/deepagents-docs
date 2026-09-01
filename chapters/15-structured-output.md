# Chapter 15 — Structured output

An agent that investigates for thirty turns and ends with a paragraph is hard to use
programmatically. `response_format` gives you a typed object alongside the transcript.

## The mechanism

```python
from pydantic import BaseModel

class Finding(BaseModel):
    root_cause: str
    confident: bool

agent = create_deep_agent(model=model, response_format=Finding)
result = agent.invoke({"messages": [...]})
```

```
keys: ['files', 'messages', 'structured_response']
structured: root_cause='disk' confident=True
```

A new key, `structured_response`, holding a validated `Finding`. Note it is **alongside**
`messages` and `files`, not instead of them — you still have the transcript and the workspace.

This is LangChain's `response_format` (Chapter 5's layering), so everything from that layer
applies: field descriptions are the prompt, `Literal` beats a described string, and it
guarantees **shape, not correctness**.

## Structured output versus a file

Here the harness gives you a choice the other layers do not, and it is worth making
deliberately.

| | `response_format` | A file |
|---|---|---|
| Typed and validated | yes | no |
| Machine-readable | immediately | you parse it |
| Length | short | any |
| Costs schema tokens every call | yes | no |
| Human-readable deliverable | no | yes |
| Available mid-run | no — only at the end | yes |

The productive pattern is **both**, and they answer different questions:

```python
class Finding(BaseModel):
    root_cause: str
    confident: bool
    report_path: str = Field(description="path of the full write-up you produced")
```

The agent writes `/findings.md` for humans and returns a small typed summary for your code —
including where the detail lives. Your caller routes on `confident`; a person reads the file.

The mistake is forcing a long report through `response_format`. It is a prompt-shaped
constraint on a document-shaped output, and it wastes the filesystem you already have.

## Make uncertainty representable

The most valuable field in a deep agent's schema is the one that lets it decline:

```python
class Finding(BaseModel):
    root_cause: str | None = Field(default=None, description="null if the evidence is insufficient")
    confident: bool
    unresolved: list[str] = Field(default_factory=list, description="what you could not determine")
```

A required `root_cause: str` forces the model to produce *something* after thirty turns of
investigation, which is exactly how a confident fabrication reaches your database. `None` is a
fact you can act on: route it to a human.

This is Chapter 12's "permission to fail", made machine-readable.

## Costs

**Schema tokens on every call.** The schema is sent as a tool definition each turn, on top of
the harness's ~2,400. A large nested model is a real per-turn cost on a long run — and unlike
your tools, you never see it used until the end.

**It constrains the ending, not the work.** The agent still investigated however it liked; the
schema only shapes the last message.

**Validation is not accuracy.** `confident=True` is the model's opinion, produced under
pressure to fill the field.

## Try it

```bash
uv run python -c "
from pydantic import BaseModel
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel

class Finding(BaseModel):
    root_cause: str
    confident: bool

m = ScriptedModel(script=[{'text':'','tool_calls':[{'name':'Finding','args':{'root_cause':'disk exhaustion','confident':True}}]}])
out = create_deep_agent(model=m, response_format=Finding).invoke({'messages':[{'role':'user','content':'go'}]})
print('keys      :', sorted(out.keys()))
print('structured:', out['structured_response'])
print('type      :', type(out['structured_response']).__name__)
"
```

Then make `root_cause` a `Literal["disk", "network"]` and have the script return
`"astrology"` — validation rejects it.

## Takeaways

- `response_format=Schema` adds **`structured_response`** to the result, **alongside**
  `messages` and `files`.
- It is LangChain's mechanism: field descriptions are the prompt, and it guarantees **shape,
  not correctness**.
- **Use both a schema and a file.** Short typed summary for your code, full write-up for
  humans — with the file's path as a field.
- Do not force a long report through `response_format`; that is what the filesystem is for.
- **Make uncertainty representable** — an optional `root_cause` and an `unresolved` list.
  A required field forces a fabrication after a failed investigation.
- Costs schema tokens on every turn, constrains only the ending, and `confident=True` is an
  opinion.

---

Previous: [Chapter 14 — Middleware and custom tools](14-middleware-and-tools.md) ·
Next: [Chapter 16 — Context management](16-context-management.md)
