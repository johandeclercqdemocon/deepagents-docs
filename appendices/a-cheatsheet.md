# Appendix A — API cheatsheet

Everything in this book on one page. Verified against the versions on the cover.

## Building

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=model,                     # required in practice; None is deprecated
    tools=[...],                     # added TO the built-ins, not instead of
    system_prompt="...",             # the WHOLE system prompt; harness adds none
    middleware=[TodoListMiddleware()],   # planning is NOT default
    subagents=[{...}],
    skills=["./skills/"],            # needs a backend that can read them
    backend=StateBackend(),          # default; see below
    interrupt_on={"write_file": True},   # needs a checkpointer to resume
    response_format=Schema,
    state_schema=MyState,            # must subclass DeepAgentState
    checkpointer=InMemorySaver(),
    store=InMemoryStore(),
)
```

> Returns a LangGraph **`CompiledStateGraph`**. `get_state`, `get_state_history`,
> `update_state`, `stream` all work.

## Running

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "..."}],     # a DICT, not a string
     "files": {"/logs/a.log": create_file_data("...")}},   # seed the workspace
    {"configurable": {"thread_id": "t"}, "recursion_limit": 40},
)

result["messages"][-1].content     # NOT result.content
result["files"]["/findings.md"]["content"]    # the actual deliverable
result["todos"]
result["structured_response"]
```

## The eight injected tools

| Tool | Note |
|---|---|
| `ls(path)` | **`path` is required** — no current directory |
| `read_file(file_path, offset?, limit?)` | returns **line-numbered** content |
| `write_file(file_path, content)` | says "Updated file" whether or not it overwrote |
| `edit_file(file_path, old_string, new_string)` | prefer over rewriting |
| `delete(file_path)` | |
| `glob(pattern, path)` | find by name |
| `grep(pattern, path)` | returns **file paths, not lines** |
| `task(description, subagent_type)` | fresh context; returns only the answer |

**Tool errors are returned as `ToolMessage`s, not raised.**

## Planning — opt in

```python
from langchain.agents.middleware import TodoListMiddleware
create_deep_agent(model=model, middleware=[TodoListMiddleware()])
```

```python
write_todos(todos=[{"content": "...", "status": "pending"}])
# statuses: pending | in_progress | completed
```

## Backends

```python
from deepagents.backends import StateBackend, FilesystemBackend, StoreBackend, CompositeBackend

StateBackend()                                        # default -- graph state, no disk
FilesystemBackend(root_dir="/scratch")                # REAL DISK
StoreBackend(namespace=lambda rt: ("mem", rt.context.user_id))   # a CALLABLE
CompositeBackend(default=StateBackend(), routes={"/memories/": StoreBackend(...)})
```

> **`virtual_mode=True` is NOT a sandbox.** It constrains paths and still writes to disk.
> **Backend factories were removed in 0.7** — pass instances.

## Subagents

```python
subagents=[{
    "name": "log-reader",
    "description": "Reads a log and reports one line.",
    "system_prompt": "...",
    "tools": [...],          # optional, its own
    "model": small_model,    # optional, its own
    "skills": ["./skills/"], # NOT inherited -- pass explicitly
}]
```

## Skills

```
skills/my-skill/SKILL.md
```

```markdown
---
name: my-skill
description: When to use this, specifically
---
```

Appear in the **system prompt**, one line each. Not tools. Need a backend.

## Approval

```python
agent = create_deep_agent(model=model, interrupt_on={"write_file": True},
                          checkpointer=InMemorySaver())

out = agent.invoke(payload, config)
if "__interrupt__" in out: ...
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
#                                          "reject" / "edit" with new args
```

## Middleware

```python
from langchain.agents.middleware import wrap_tool_call, TodoListMiddleware, ModelCallLimitMiddleware
from langchain_core.messages import ToolMessage

@wrap_tool_call
def guard(request, handler):
    if request.tool_call["name"] == "delete":
        return ToolMessage(content="Refused.",              # a ToolMessage, NOT a string
                           tool_call_id=request.tool_call["id"])
    return handler(request)
```

| Middleware | For |
|---|---|
| `TodoListMiddleware` | planning — **not default** |
| `ModelCallLimitMiddleware(run_limit=30)` | graceful cap; defaults to `exit_behavior="end"` |
| `ToolCallLimitMiddleware` | **pass `exit_behavior="end"`** or it does not stop the loop |
| `SummarizationMiddleware` | compress history; takes a `backend` |
| `RubricMiddleware` | grade artefacts |

## Custom tools

```python
@tool(parse_docstring=True)     # WITHOUT THIS, Args: descriptions are DROPPED
def check_metric(name: str) -> str:
    """What it does, and when to use it.

    Args:
        name: One of "a", "b", "c".
    """
```

## Diagnostics

```python
model.bound_tools              # what the model ACTUALLY had -- the top check
[m for m in result["messages"] if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)]
sorted(result["files"])        # did it produce anything?
result.get("todos")            # where did it think it was?
agent.get_state(config).next, .interrupts
for h in agent.get_state_history(config): ...      # when each file appeared
agent.stream(payload, stream_mode="updates", subgraphs=True)   # inside subagents
```

## Numbers worth remembering

| | |
|---|---|
| Injected tools | **8** |
| Tool definitions per call | **~2,414 tokens** |
| A 6-turn run | ~14,500 tokens of overhead |
| Default `recursion_limit` | **10007** |
| Sensible `recursion_limit` | 30–60 |
| Todo statuses | `pending`, `in_progress`, `completed` |

## The six silent failures

1. **Planning off by default** — no `TodoListMiddleware`, no `write_todos`.
2. **Skills with no backend** — configured, never loaded.
3. **No checkpointer** — files vanish between runs; approval cannot resume.
4. **`@tool` without `parse_docstring=True`** — argument descriptions dropped.
5. **`virtual_mode=True`** — not a sandbox; still writes to disk.
6. **Tool errors returned, not raised** — the agent narrates over them.

## Which library owns the error

| Mentions | Look in |
|---|---|
| `InvalidUpdateError`, `GraphRecursionError`, checkpointer, thread, interrupt | **LangGraph** |
| tool schemas, `parse_docstring`, `response_format`, middleware, models | **LangChain** |
| backends, skills, subagents, `write_todos`, filesystem tools | **Deep Agents** |

---

Next: [Appendix B — Glossary](b-glossary.md)
