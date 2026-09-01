# Chapter 24 — Structuring a real project

Everything so far has been a snippet. This chapter is what changes when a deep agent has to
live in an application.

## A layout that works

```
src/scout/
  models.py       # model construction, one place
  prompts.py      # the system prompt, versioned with the code
  tools.py        # custom tools
  subagents.py    # subagent definitions
  skills/         # SKILL.md directories -- in the repo, in review
  backend.py      # which backend, and its routing
  agent.py        # assembles it
  app.py          # the web layer
tests/
  test_config.py  # is each capability actually enabled?
  test_agent.py   # scripted-model behaviour
```

The unusual file is `test_config.py`. In this library, **whether a capability is present is
itself worth testing** (Chapter 6, Chapter 10), because absence is silent.

Skills belong in the repository. They are prompt-shaped content that changes behaviour; a
skill edited on a server is an unreviewable deployment.

## Build in a function

```python
def build_agent(*, model=None, backend=None, checkpointer=None, store=None):
    return create_deep_agent(
        model=model or parent_model(),
        tools=TOOLS,
        subagents=SUBAGENTS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[TodoListMiddleware(), *AUDIT],
        backend=backend or default_backend(),
        skills=["./skills/"],
        checkpointer=checkpointer,
        store=store,
    )
```

Never at import time — importing your package should not construct model clients or open
connections. Taking the model and backend as arguments is what lets tests inject a
`ScriptedModel` and a `StateBackend`.

Build once at startup and reuse; the compiled graph is safe to invoke concurrently.

The book's example does this with a `todos=` flag so Chapter 6 can demonstrate both states —
see [`examples/scout/agent.py`](../examples/scout/agent.py).

## Backend and checkpointer are deployment decisions

The two arguments with the largest blast radius:

| | Development | Production |
|---|---|---|
| Backend | `StateBackend()` | `CompositeBackend` routing durable paths to `StoreBackend` |
| Checkpointer | `InMemorySaver()` | **Postgres** |
| Store | `InMemoryStore()` | Postgres |

**The moment you run two workers, in-memory anything is wrong.** A paused approval
(Chapter 13) cannot be resumed by a different worker, and files vanish between requests.

If you use `FilesystemBackend`, its `root_dir` is a security boundary. Point it at a scratch
directory, never at your source tree, and pair it with approval on writes.

## The web layer

```python
@asynccontextmanager
async def lifespan(app):
    async with AsyncPostgresSaver.from_conn_string(DB_URL) as checkpointer:
        await checkpointer.setup()
        app.state.agent = build_agent(checkpointer=checkpointer)
        yield

@app.post("/investigate/{incident_id}")
async def investigate(incident_id: str, body: Request):
    config = {"configurable": {"thread_id": f"incident-{incident_id}"},
              "recursion_limit": 40}
    result = await app.state.agent.ainvoke(
        {"messages": [{"role": "user", "content": body.question}], "files": seed(incident_id)},
        config)
    if "__interrupt__" in result:
        return {"status": "pending_approval", "thread_id": f"incident-{incident_id}"}
    return {"answer": result["messages"][-1].content,
            "report": result["files"].get("/findings.md", {}).get("content")}
```

Four things this gets right: the agent is built once, the checkpointer's lifetime is the
application's, `recursion_limit` is set (Chapter 21), and **the response returns the file, not
just the message** — the file is the deliverable.

A deep agent takes minutes, so a synchronous HTTP request is usually wrong. Return a
`thread_id` immediately and let the client poll `get_state`, or run it on a queue.

## Configuration

| Kind | Home |
|---|---|
| API keys, database URLs, model names | environment |
| Tenant, user id, incident id | per-request context |
| `recursion_limit`, call limits, which tools need approval | **code** |
| The system prompt and skills | **the repository** |

The third row is an opinion worth holding. Limits look like configuration and behave like
behaviour: raising `recursion_limit` changes what the agent does and what it costs. Put it in
code so it goes through review.

## Test the configuration

The habit specific to this library:

```python
def test_planning_is_opt_in():
    assert "write_todos" not in _offered()
    assert "write_todos" in _offered(middleware=[TodoListMiddleware()])

def test_system_prompt_names_the_output_path():
    assert "/findings.md" in SYSTEM_PROMPT
```

Both guard silent failures. Chapter 25 builds this out.

## Pin your versions

```toml
dependencies = [
    "deepagents>=0.7,<1",
    "langchain>=1.3,<2",
    "langgraph>=1.2,<2",
]
```

Deep Agents is pre-1.0 and moving fastest of the three. Pin all three — a LangChain or
LangGraph change can alter behaviour here without deepagents changing at all, which is the
cost of sitting on top of a stack.

## Try it

See the assembly separated from the running:

```bash
uv run python -c "
from examples.scout.agent import build
from examples.scout.workspace import seed

agent = build()                      # constructed once
out = agent.invoke({'messages':[{'role':'user','content':'why did node-3 fail?'}], 'files': seed()},
                   {'recursion_limit': 40})
print('report:', bool(out['files'].get('/findings.md')))
print('todos :', len(out.get('todos', [])))
"
```

Then confirm the injection point that makes tests possible:

```bash
uv run python -c "
from examples.scout.agent import build
from examples.scout.fakes import ScriptedModel
out = build(model=ScriptedModel(script=['injected reply'])).invoke(
    {'messages':[{'role':'user','content':'hi'}]})
print(out['messages'][-1].content)
"
```

## Takeaways

- Separate models, prompts, tools, subagents, skills, backend and assembly. **Skills belong in
  the repository** — they change behaviour and should be reviewed.
- **Build in a function, never at import time**, taking model, backend and checkpointer as
  arguments so tests can inject fakes. Build once at startup.
- Backend and checkpointer are **deployment decisions**. Two workers means Postgres and no
  in-memory anything.
- `FilesystemBackend`'s `root_dir` is a security boundary — scratch directory, plus approval
  on writes.
- In the web layer: build once, set `recursion_limit`, and **return the file, not just the
  message**. A minutes-long agent usually wants a job and a `thread_id`, not a blocking request.
- Secrets in the environment; tenant per request; **limits and prompts in code**, because they
  are behaviour.
- **Test that capabilities are enabled** — in this library, absence is silent.
- Pin all three packages; deepagents is pre-1.0 and sits on two moving layers.

---

Previous: [Chapter 23 — Cookbook](23-cookbook.md) ·
Next: [Chapter 25 — Testing](25-testing.md)
