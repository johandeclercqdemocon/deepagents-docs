# Chapter 23 — Cookbook: symptom → cause → fix

Indexed by what you see. Every message was produced by running code against the versions on
the cover.

## Exceptions

### `InvalidUpdateError: Expected dict, got hello`

You passed a string. Agents take `{"messages": [...]}`. From LangGraph. → Ch 19

### `AttributeError: 'dict' object has no attribute 'content'`

The result is a dict: `result["messages"][-1].content`. → Ch 19

### `TypeError: backend must be an initialized backend instance. Backend factories were removed in deepagents 0.7`

`backend=lambda rt: StoreBackend(rt)` no longer works. Pass an instance. Most published
examples are stale. → Ch 8

### `TypeError: 'tuple' object is not callable`

`StoreBackend(namespace=("memories",))`. It takes a **callable** —
`namespace=lambda rt: ("memories",)`. Raised inside the write, so the traceback points at
`store.py`. → Ch 8

### `RuntimeError: Cannot use Command(resume=...) without checkpointer`

Approval configured with no checkpointer. Note the pause itself worked. → Ch 13

### `GraphRecursionError: Recursion limit of N reached`

The agent did not stop. **The default is 10007** — set it explicitly, 30–60 for real work.
Then check whether a tool result permits stopping. → Ch 21

### `LangChainDeprecationWarning: Passing model=None ... deprecated`

Pass a model explicitly; it breaks at deepagents 1.0. → Ch 19

### `ValidationError` from `write_todos`

A status outside `pending` / `in_progress` / `completed`. → Ch 6

## Silent — no error at all

These are the expensive ones.

### The agent never plans

`write_todos` is **not enabled by default**. Add `TodoListMiddleware` from
`langchain.agents.middleware`. Verify with `model.bound_tools`. → Ch 6

### A skill never loads

Either no backend (`skills=[...]` alone does nothing) or a description that does not say when
to use it. Check the skill's name appears in the system prompt. → Ch 10

### Files disappear between runs

No checkpointer. Measured: `run1 files: ['/a.md'] | run2 files: []`. → Ch 4

### Your tool's argument descriptions are missing

`@tool` without `parse_docstring=True`. Check `my_tool.args`. → Ch 14

### `FilesystemBackend(virtual_mode=True)` wrote to your disk

**`virtual_mode` is not a sandbox.** It constrains paths, not access. For files that never
touch disk use `StateBackend` — the default. → Ch 8

### `ToolCallLimitMiddleware` did not stop the loop

`exit_behavior` defaults to `"continue"`. Pass `exit_behavior="end"`. → Ch 21

### A middleware refusal appears as the user speaking

`wrap_tool_call` returning a bare string produces a `HumanMessage`. Return a
`ToolMessage(content=..., tool_call_id=request.tool_call["id"])`. → Ch 13

### Delegation "isn't helping"

A typo'd `subagent_type` is returned as a tool result — *"We cannot invoke subagent nope"* —
not raised. The agent then does the work itself. → Ch 19

### The agent narrates confidently over a broken filesystem

Tool errors are returned, not raised. Scan for them:

```python
[str(m.content)[:60] for m in result["messages"]
 if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)]
```
→ Ch 18

## Behaviour

### It writes to the wrong path

You did not say where. Name every path you will read. → Ch 12

### It reads whole files it does not need

No `grep` first. Prompt for locate-then-read. Symptom: `ToolMessage`s of thousands of
characters. → Ch 7, 16

### It plans once and never updates

Ask: *"Mark each item complete as you finish it."* A stale plan is worse than none. → Ch 6

### It never delegates

`task` is under-used because its benefit is invisible to the model. Name the subagent and the
trigger. → Ch 9

### A subagent's answer is useless

The `description` is the entire brief and there is no follow-up. → Ch 9

### A subagent ignores a skill the parent follows

**Skills are not inherited.** Pass them to the subagent explicitly. → Ch 10

### It fabricates a conclusion

Missing evidence (check tool errors; permit failing) or misread evidence (a model problem).
**Citations distinguish them.** → Ch 12, 20

### It repeats work it already did

Context loss. Write findings to files earlier — files survive summarisation, transcripts do
not. → Ch 16

### It stops too early

"Done" was never defined. *"You are finished when /findings.md exists and every todo is
complete."* → Ch 20

### Quality degrades as the run goes on

Context, not capability. → Ch 16

### The chat UI shows raw file contents

`stream_mode="messages"` includes tool output. Filter on `langgraph_node`. → Ch 22

## Fast diagnostics

```python
# what tools did the model ACTUALLY have -- the highest-value check
model.bound_tools

# what did it do
for m in result["messages"]:
    print(type(m).__name__, str(m.content)[:80])

# did any tool fail?
[str(m.content)[:60] for m in result["messages"]
 if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)]

# what did it produce -- the actual deliverable
sorted(result["files"]); result["files"]["/findings.md"]["content"]

# where did it think it was
result.get("todos")

# is the skill loaded?  (look for its name in the system prompt)
# is it paused?
snap = agent.get_state(config); snap.next, snap.interrupts

# when did each file appear
for h in agent.get_state_history(config):
    print(h.metadata.get("step"), sorted(h.values.get("files", {})))

# inside subagents
for ns, chunk in agent.stream(payload, stream_mode="updates", subgraphs=True): ...
```

## The silent failures, in one place

1. **Planning off by default** — no `TodoListMiddleware`, no `write_todos`. → Ch 6
2. **Skills without a backend** — configured, never loaded. → Ch 10
3. **No checkpointer** — files vanish between runs; approval cannot resume. → Ch 4, 13
4. **`@tool` without `parse_docstring=True`** — argument descriptions dropped. → Ch 14
5. **`virtual_mode=True` is not a sandbox** — still writes to disk. → Ch 8
6. **Tool errors are returned, not raised** — the agent narrates over them. → Ch 18

## Which library owns the error

| Mentions | Look in |
|---|---|
| `InvalidUpdateError`, `GraphRecursionError`, checkpointer, thread, interrupt | **LangGraph** |
| tool schemas, `parse_docstring`, `response_format`, middleware, models | **LangChain** |
| backends, skills, subagents, `write_todos`, filesystem tools | **Deep Agents** |

→ Ch 5

---

Previous: [Chapter 22 — Observing a long run](22-observing.md) ·
Next: [Chapter 24 — Structuring a real project](24-project-structure.md)
