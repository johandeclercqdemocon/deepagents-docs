# Chapter 2 — Your first deep agent

This chapter builds the smallest possible deep agent and looks at what arrived without being
asked for. It assumes `scripts/verify.py` passed. No API key; no model is called.

## The whole program

```python
from deepagents import create_deep_agent

agent = create_deep_agent(model=model)

result = agent.invoke({"messages": [{"role": "user", "content": "hello"}]})
print(result["messages"][-1].content)
```

```
reply: Nothing to investigate.
```

That is a complete deep agent. One call, no tools of your own, no configuration.

Note the input and output shape, because it is the same as a LangChain agent and the first
thing people get wrong:

```python
agent.invoke({"messages": [{"role": "user", "content": "..."}]})   # a dict, not a string
result["messages"][-1].content                                      # not result.content
```

## What arrived uninvited

Ask what the model was actually offered:

```
state keys:     ['files', 'messages']
tools injected: 8 ['ls', 'read_file', 'write_file', 'edit_file', 'delete', 'glob', 'grep', 'task']
```

**Eight tools you did not write**, and a state field called `files` you did not declare.

That is the harness. Seven of the tools are a filesystem; the eighth, `task`, spawns
subagents. Chapter 3 covers what each does and Chapter 4 covers where the files live.

What is *not* there is worth as much: no `write_todos`. Planning is opt-in, and Chapter 6 is
about that discrepancy.

## Adding your own tools

Exactly as in LangChain — the harness's tools are additive, not a replacement:

```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def check_metric(name: str) -> str:
    """Look up the current value of a named infrastructure metric.

    Args:
        name: One of "disk_used_pct", "jitter_ms", "error_rate".
    """
    return {"disk_used_pct": "node-3 disk_used_pct = 97"}.get(name, f"unknown metric {name!r}")

agent = create_deep_agent(model=model, tools=[check_metric])
```

The model now sees nine tools: your one and the harness's eight.

> **`@tool` does not parse the `Args:` docstring by default.** Without `parse_docstring=True`
> your argument descriptions are silently dropped and the model sees a bare `name: string`.
> That is a LangChain behaviour inherited here, and it is the single most common
> quietly-broken tool.

## The system prompt

```python
agent = create_deep_agent(model=model, system_prompt="You investigate incidents.")
```

Something surprising, measured: with no skills configured, the harness's own system prompt is
**empty**.

```
system prompt: 0 chars
with a system_prompt of your own: 26 chars, yours at position 0
```

Your prompt is the whole system prompt. The harness does not prepend a wall of instructions —
the guidance lives in the *tool descriptions* instead, which is why Chapter 1 measured ~2,400
tokens there. Configure skills (Chapter 10) and a "Skills System" section does appear.

Practically: **your `system_prompt` is not competing with a hidden preamble.** Say what the
agent is for, what it should write where, and what to do when the evidence is thin:

```python
SYSTEM_PROMPT = """You investigate production incidents.

Work from the files you are given. Read the logs, check the config against the
runbooks, and write your conclusion to /findings.md. Cite the file each claim
came from. If the evidence does not support a conclusion, say so."""
```

Three things that earn their place: **where to write output**, **a citation rule**, and
**permission to fail**. Chapter 12 goes further.

## The result

`invoke` returns a dict, and its keys grow as you enable capabilities:

| Key | Present when |
|---|---|
| `messages` | always |
| `files` | always — the virtual filesystem (Chapter 7) |
| `todos` | you added `TodoListMiddleware` (Chapter 6) |

The message list is the reasoning trace and your main debugging tool (Part IV). The `files`
dict is the actual work product — for `scout`, the report matters more than anything the
agent said.

## Try it

Build the smallest agent and look at what you got:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel

model = ScriptedModel(script=['Nothing to investigate.'])
agent = create_deep_agent(model=model)
out = agent.invoke({'messages':[{'role':'user','content':'hello'}]})
print('reply      :', out['messages'][-1].content)
print('state keys :', sorted(out.keys()))
print('tools       :', model.bound_tools)
"
```

Eight tools from one line of configuration. Now add one of your own and watch it become nine:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langchain_core.tools import tool
from examples.scout.fakes import ScriptedModel

@tool(parse_docstring=True)
def check_metric(name: str) -> str:
    '''Look up a metric.

    Args:
        name: the metric name
    '''
    return 'ok'

model = ScriptedModel(script=['done'])
create_deep_agent(model=model, tools=[check_metric]).invoke({'messages':[{'role':'user','content':'hi'}]})
print(model.bound_tools)
print('your tool sees descriptions:', check_metric.args)
"
```

Then drop `parse_docstring=True` and confirm the description disappears.

## Takeaways

- `create_deep_agent(model=...)` is a complete agent. Input and output are dicts keyed on
  `messages`; read `result["messages"][-1].content`.
- **Eight tools arrive uninvited** — seven filesystem operations plus `task` — along with a
  `files` state field. That is the harness.
- `write_todos` is **not** among them. Planning is opt-in (Chapter 6).
- Your tools are added to the harness's, not swapped for them.
- **`@tool` needs `parse_docstring=True`** or your argument descriptions are silently dropped.
- With no skills configured the harness's **system prompt is empty** — yours is the whole
  thing, and it is not competing with a hidden preamble.
- A good system prompt says **where to write output**, **how to cite**, and **that admitting
  ignorance is allowed**.
- The result's `files` dict is usually the real work product, not the final message.

---

Previous: [Chapter 1 — Why Deep Agents](01-why-deep-agents.md) ·
Next: [Chapter 3 — The built-in tools](03-built-in-tools.md)
