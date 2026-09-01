# Chapter 32 — Anti-patterns

Things that look reasonable and are not, each with the reason and the fix. Most were measured
earlier in this book.

## Choosing the layer

### Using a deep agent for a short task

**Why it hurts:** ~2,400 tokens of tool definitions on every call for machinery it does not
use. A three-turn task pays ~7,000 tokens for a filesystem it never opens.

**Fix:** `create_agent`. Reach for the harness when the task is long and context is the
problem.

### Using a deep agent when the steps are known

**Why it hurts:** you pay a model to rediscover a sequence you already know, and lose
predictability.

**Fix:** a chain, or a LangGraph graph (Chapter 31).

### Fighting the harness's opinions

**Why it hurts:** you cannot remove the built-in middleware, rename its tools, or change the
loop's shape. Effort spent here is wasted.

**Fix:** write a graph. Or compose — harness for the open-ended part, graph around it.

### Building a hierarchy of agents

**Why it hurts:** every level is a model call, context is lost at each boundary, and debugging
spans transcripts none of which tells the whole story.

**Fix:** one level of delegation. Three means the design got away from you.

## Configuration that silently does nothing

### Expecting planning by default

**Why it hurts:** **`write_todos` is not enabled in 0.7.11**, despite what nearly everything
written about Deep Agents says. The agent works, never plans, and loses the thread on long
tasks.

**Fix:** `middleware=[TodoListMiddleware()]`, and a test asserting it (Chapter 25).

### `skills=[...]` with no backend

**Why it hurts:** builds without error; the skill never appears in the system prompt.

**Fix:** a backend that can read them. Verify the skill's name is in the prompt.

### No checkpointer

**Why it hurts:** files vanish between invocations — measured, `run2 files: []` — and approval
cannot resume.

**Fix:** a checkpointer and a stable `thread_id`.

### `@tool` without `parse_docstring=True`

**Why it hurts:** argument descriptions dropped silently, and with eight built-in tools
competing, a vague schema means an unused tool.

**Fix:** `parse_docstring=True` or an explicit `args_schema`, plus the test from Chapter 25.

### Backend factories

**Why it hurts:** `backend=lambda rt: StoreBackend(rt)` was removed in 0.7 and raises. Most
published examples still show it.

**Fix:** pass an instance.

### A tuple `StoreBackend` namespace

**Why it hurts:** raises `TypeError: 'tuple' object is not callable` from inside the write, so
the traceback points at the library.

**Fix:** `namespace=lambda rt: ("memories",)`.

## The filesystem

### Mistaking `virtual_mode=True` for a sandbox

**Why it hurts:** it constrains paths and **still writes to your disk**. The name invites
exactly this error.

**Fix:** `StateBackend` for files that must not touch disk. If you need real files: scratch
`root_dir`, approval on writes.

### Not telling the agent where to write

**Why it hurts:** it invents a path and your `result["files"]["/findings.md"]` raises
`KeyError`.

**Fix:** name every path you will read, in the system prompt.

### Letting the agent read whole files

**Why it hurts:** the original context problem, now with ~2,400 tokens of overhead on top.

**Fix:** prompt for `grep` before `read_file`, and `offset`/`limit`. Symptom: `ToolMessage`s of
thousands of characters.

### Seeding enormous files

**Why it hurts:** everything in `files` is in every checkpoint.

**Fix:** a backend that is not state, or seed a path and let the agent fetch.

### Reading the final message instead of the file

**Why it hurts:** **the file is the work; the message is a summary.** They fail differently,
and a run that wrote nothing can still narrate confidently.

**Fix:** read `result["files"]`, and assert it is non-empty.

## Subagents and skills

### A vague `description` on a `task` call

**Why it hurts:** it is the entire brief and there is no follow-up. A vague brief produces a
confident, useless answer the parent cannot detect.

**Fix:** specific briefs. *"Report the first ERROR line with its timestamp, or say none
found."*

### Delegating small subtasks

**Why it hurts:** each delegation pays a full model call plus the tool block. A subagent saving
500 tokens costs more than it saves.

**Fix:** delegate bulky reads only.

### Expecting subagents to inherit skills

**Why it hurts:** they do not. A subagent ignores the house format while the parent obeys it —
confusing, because the skill demonstrably works.

**Fix:** pass `skills` to the subagent explicitly.

### A skill that never loads

**Why it hurts:** the routing decision is the description alone, and rejection is silent.

**Fix:** say *when* to use it, specifically.

## Operations

### Not setting `recursion_limit`

**Why it hurts:** **the default is 10007**, and a deep agent turn is expensive.

**Fix:** 30–60 explicitly, plus `ModelCallLimitMiddleware` for a graceful stop.

### Using `ToolCallLimitMiddleware` with defaults as a cost guard

**Why it hurts:** `exit_behavior` defaults to `"continue"` — it blocks calls without stopping
the loop.

**Fix:** `exit_behavior="end"`.

### Returning a bare string from `wrap_tool_call`

**Why it hurts:** it becomes a `HumanMessage`, so a refusal reads as the user speaking.

**Fix:** a `ToolMessage` with the matching `tool_call_id`.

### Running it as a synchronous HTTP request

**Why it hurts:** minutes-long, and it may pause for a human.

**Fix:** a job and a `thread_id`; poll `get_state`.

### In-memory checkpointer with more than one worker

**Why it hurts:** polling, approval and resume all break.

**Fix:** Postgres.

### No checkpoint retention policy

**Why it hurts:** deep agents produce many supersteps, each a checkpoint holding every file.

**Fix:** prune finished threads. Cost *and* privacy.

### Renaming a subagent with live threads

**Why it hurts:** paused threads resume against today's code, mid-delegation, and fail with no
deploy-time error.

**Fix:** treat subagent names and the state schema as a public interface; drain before
structural changes.

## Trust

### Letting the agent write its own long-term memory

**Why it hurts:** it reads its own speculation back as fact, and an injected instruction
written to memory **persists across sessions**.

**Fix:** write memory from deterministic code, or review before promoting.

### Trusting seeded documents

**Why it hurts:** anything the agent reads can instruct it, with the authority of your own
workspace.

**Fix:** structural controls — narrow tools, scope from context, a backend that reaches
nothing precious.

### Believing the agent when it says it succeeded

**Why it hurts:** tool errors are returned, not raised, so it narrates confidently over a
broken filesystem.

**Fix:** scan `ToolMessage`s for `Error`, and assert a file was produced.

## Testing

### Not testing that capabilities are enabled

**Why it hurts:** in this library, absence is silent. Behavioural tests pass while the agent
is missing a capability you designed for.

**Fix:** assert on `bound_tools` and on the system prompt's load-bearing lines.

### Asserting on generated prose

**Why it hurts:** breaks on any rewording.

**Fix:** assert on **files, todos and citations** — structure, not words.

## A review checklist

- [ ] Is `TodoListMiddleware` present if the agent should plan?
- [ ] Do all custom tools use `parse_docstring=True`?
- [ ] Does the system prompt name every output path you read?
- [ ] Does it permit failing?
- [ ] Is `recursion_limit` set, and a call limit?
- [ ] Is the backend right — and have you mistaken `virtual_mode` for a sandbox?
- [ ] Is tenant scope taken from context, in the namespace tuple?
- [ ] Do subagents have the skills and constraints they need?
- [ ] Does a test assert the run produced a file and no tool errored?
- [ ] Is there a checkpoint retention policy?

## Takeaways

- Most anti-patterns here are one of three things: **using more machinery than the problem
  needs**, **trusting a default that does not do what its name suggests**, or **believing the
  agent's narration over its tool results**.
- The library will not warn you. The silent failures — planning off, skills unloaded, no
  checkpointer, dropped tool descriptions, `virtual_mode` writing to disk, returned tool
  errors — are the expensive ones precisely because nothing tells you.
- The checklist takes two minutes and catches most of them.

---

Previous: [Chapter 31 — Deep Agents, LangChain and LangGraph](31-the-stack.md) ·
Back to the [table of contents](../README.md)
