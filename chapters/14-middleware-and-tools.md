# Chapter 14 — Middleware and custom tools

The harness is opinionated, which is its value and its constraint. This chapter is the two
supported ways to change it: adding tools, and wrapping the loop.

## Custom tools

Your tools sit alongside the harness's eight (Chapter 2):

```python
@tool(parse_docstring=True)
def check_metric(name: str) -> str:
    """Look up the current value of a named infrastructure metric.

    Args:
        name: One of "disk_used_pct", "jitter_ms", "error_rate".
    """
    return {"disk_used_pct": "node-3 disk_used_pct = 97"}.get(name, f"unknown metric {name!r}")

agent = create_deep_agent(model=model, tools=[check_metric])
```

Everything from the LangChain layer applies, and three points bear repeating here because the
harness makes them sharper.

**`parse_docstring=True` or your argument descriptions are dropped**, silently. With eight
built-in tools already competing for the model's attention, a tool with a vague schema is one
it will not choose.

**Say when to use it, and how it relates to the files.** *"Prefer this over reading
`/metrics/`; it is live."* The model is choosing between your tool and `read_file`, and
nothing else tells it which is authoritative.

**Return text the model can act on.** `"unknown metric 'foo'"` naming the valid options ends
the loop; a bare `"error"` invites another guess.

### Tools versus files

A genuine design question the other books do not have. When should a capability be a tool, and
when should it be a file the agent reads?

| | Tool | File |
|---|---|---|
| Live data | yes | no |
| Large reference text | no — it all enters context | yes — read on demand |
| Actions with effects | yes | no |
| Something written once, read often | no | yes |

The mistake is a tool that returns 40 KB of documentation. That is a file — write it into the
workspace at seed time and let the agent `grep` it.

## Middleware

Middleware wraps stages of the loop. `wrap_tool_call` is the one you will use:

```python
from langchain.agents.middleware import wrap_tool_call

@wrap_tool_call
def audit(request, handler):
    result = handler(request)
    log.info("tool=%s args=%s", request.tool_call["name"], request.tool_call["args"])
    return result

agent = create_deep_agent(model=model, middleware=[audit])
```

Note that `middleware=` is also how you **add** harness capabilities — `TodoListMiddleware`
for planning (Chapter 6) arrives this way. It is not only for your own hooks.

Worth building:

**Path enforcement.** Chapter 13's rule: refuse writes outside `/scratch/`, and say what is
allowed.

**Auditing.** Every filesystem operation, with the thread id. On an agent that writes files
this is the record you will want when someone asks what it changed.

**Scope injection.** Rewrite arguments so the tenant comes from your context, never the
model's (Chapter 28).

**Cost accounting.** Count tool calls and tokens per run (Chapter 27).

Two mechanics from the LangChain layer:

- Return a **`ToolMessage`**, not a string, when short-circuiting — a bare string becomes a
  `HumanMessage`, so a refusal reads as the user speaking.
- Order matters: middleware nests, first in the list outermost.

## Extending state

`state_schema` adds fields to the graph state:

```python
from deepagents import DeepAgentState

class ScoutState(DeepAgentState):
    severity: str

agent = create_deep_agent(model=model, state_schema=ScoutState)
agent.invoke({"messages": [...], "severity": "high"})
```

```
keys: ['files', 'messages', 'severity'] | severity kept: high
```

Subclass `DeepAgentState` — it carries `files` and the rest. Subclassing the wrong thing gives
you an agent with no filesystem.

**Usually you should not.** A file is a better place for anything the agent produces, because
a file has a name the agent can reason about and a custom state field does not. Reach for
`state_schema` for values *your code* sets and reads — a tenant id, a severity, a request
correlation id — not for the agent's output.

## What you cannot change

The boundary is real:

- **The built-in middleware is always present.** You cannot remove the filesystem or subagent
  tools.
- **Tool names are fixed.** No renaming `write_file`.
- **The loop's shape is fixed** — model, tools, repeat.

If you are fighting these, you want a graph (Chapter 31). The harness gives up flexibility for
a month of saved work; when that trade stops paying, take the other side of it.

## Try it

Add a tool and watch it join the eight:

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

m = ScriptedModel(script=['done'])
create_deep_agent(model=m, tools=[check_metric]).invoke({'messages':[{'role':'user','content':'hi'}]})
print(m.bound_tools)
print('schema the model sees:', check_metric.args)
"
```

Then intercept every tool call:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_tool_call
from examples.scout.fakes import ScriptedModel

seen = []
@wrap_tool_call
def audit(request, handler):
    seen.append(request.tool_call['name'])
    return handler(request)

script = [{'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/a.md','content':'1'}}]},
          {'text':'y','tool_calls':[{'name':'ls','args':{'path':'/'}}]}, 'done']
create_deep_agent(model=ScriptedModel(script=script), middleware=[audit]).invoke(
    {'messages':[{'role':'user','content':'go'}]})
print('intercepted:', seen)
"
```

## Takeaways

- Custom tools are **added to** the harness's eight, not swapped for them.
- **`parse_docstring=True`** or your argument descriptions vanish — and with eight tools
  already competing, a vague schema means an unused tool.
- Say **when to use your tool relative to the files**; nothing else tells the model which is
  authoritative.
- **A tool returning 40 KB of reference text should be a file.** Live data and actions are
  tools; large text read on demand is a file.
- `middleware=` both adds your hooks and **enables harness capabilities** like
  `TodoListMiddleware`.
- Short-circuit with a **`ToolMessage`**, not a string. Order nests, first is outermost.
- `state_schema` must subclass **`DeepAgentState`**, and is for values *your code* sets — a
  file is the better home for the agent's output.
- You cannot remove the built-in middleware, rename its tools, or change the loop's shape. If
  you need to, write a graph.

---

Previous: [Chapter 13 — Permissions and approval](13-permissions.md) ·
Next: [Chapter 15 — Structured output](15-structured-output.md)
