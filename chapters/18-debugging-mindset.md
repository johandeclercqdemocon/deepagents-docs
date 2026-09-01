# Chapter 18 — The debugging mindset

A deep agent is harder to debug than a chain for a specific reason: it is long, it is
non-deterministic, and **most of what it did is not in the final message**. The answer looks
wrong; the cause is thirty turns back, in a file, or inside a subagent whose work you cannot
see.

The cure is to stop reading the output and start reading the run.

## Four layers, three libraries

Chapter 5 established the stack. Debugging follows it:

| # | Layer | Question | Chapter |
|---|---|---|---|
| 1 | **Configuration** | Is the capability even enabled? | 19 |
| 2 | **Harness** | Did it plan, read, delegate, write correctly? | 20 |
| 3 | **Model** | Given what it saw, was the reasoning sound? | 20 |
| 4 | **Runtime** | State, persistence, limits | 21 |

Layer 1 is first because it is the cheapest and, in this library, the likeliest. Three things
are silently absent unless you ask for them:

- **`write_todos`** — no `TodoListMiddleware`, so no planning (Chapter 6).
- **Skills** — no backend, so `skills=[...]` did nothing (Chapter 10).
- **Files across runs** — no checkpointer, so each `invoke` starts empty (Chapter 4).

None of these produce an error. The agent simply works worse than you designed it to.

## The one-minute triage

Four things to look at, in order, before forming any theory.

**1. What tools did the model actually have?**

```python
model.bound_tools     # with a scripted model, or read your trace
```

The single highest-value check in this book. Half of "the agent won't plan" is `write_todos`
not being there.

**2. What did it do?**

```python
for m in result["messages"]:
    print(type(m).__name__, str(m.content)[:80])
```

The message list is the reasoning trace. Read the `ToolMessage`s especially — a run where
every `read_file` returned `File not found` looks like a confused model and is a wrong path.

**3. What did it produce?**

```python
sorted(result["files"])
result["files"]["/findings.md"]["content"]
```

**The file is the work; the final message is a summary.** An agent that wrote a good report
and summarised it badly is a different problem from one that concluded wrongly.

**4. Where did it think it was?**

```python
result.get("todos")
```

A plan with everything still `pending` after forty turns means the agent never followed it.
An unchanged plan is the clearest "stuck" signal available.

## Read tool results, not conclusions

The habit that matters most. A deep agent narrates confidently regardless of whether its tools
worked, because tool errors come back as ordinary `ToolMessage`s (Chapter 3):

```
read missing -> "Error: File '/nope.md' not found"
```

The run succeeds. The agent says *"I was unable to locate the configuration, but based on the
logs..."* and produces something plausible. Nothing raised.

So: **scan the `ToolMessage`s for the word `Error` before anything else.**

```python
[str(m.content)[:60] for m in result["messages"]
 if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)]
```

## Subagent work is invisible

By design (Chapter 9). The parent's transcript contains a subagent's one-line answer and none
of its reasoning. If the answer is wrong you cannot see why from the parent.

Three ways in:

- **Have subagents write files.** Then their work is inspectable after the fact.
- **Stream with `subgraphs=True`** (Chapter 22).
- **Suspect the `description`.** The brief is the whole instruction, and an underspecified one
  produces a confident, useless answer.

## Make it reproducible

Two sources of variance, both removable:

**The model.** Replace it with a `ScriptedModel` replaying the exact calls from the failing
run. If the bug survives with fixed replies, it is your code — and now it is free to iterate
on.

**The state.** A bug on a thread with history is not reproducible from a fresh input. Note
whether you are testing a new thread or a resumed one, and what was in `files` at the start.

## Bisect the capabilities

Deep agents have unusually good bisection, because each capability can be switched off:

```python
build(todos=False)                  # is planning confusing it?
create_deep_agent(model=m, tools=[])# is a custom tool misleading it?
# drop subagents=[...]              # is delegation losing information?
# swap backend for StateBackend()   # is the backend the problem?
```

Turn off one capability at a time. The one whose removal fixes it is implicated — and often
the answer is that a capability was never doing what you assumed.

## Try it

Practise reading a run rather than its answer:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
print('--- what it did')
for m in out['messages']:
    print(f'  {type(m).__name__:13} {str(m.content)[:52]}')
print('--- what it produced')
print(' ', sorted(out['files']))
print('--- where it thought it was')
for t in out.get('todos', []): print(f\"  [{t['status']:11}] {t['content']}\")
"
```

Then the error scan, which should be empty here:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
errs = [str(m.content)[:70] for m in out['messages']
        if type(m).__name__ == 'ToolMessage' and 'Error' in str(m.content)]
print('tool errors:', errs or 'none')
"
```

Now break it: change `/runbooks/disk.md` to `/runbooks/nope.md` in the script in
[`examples/scout/agent.py`](../examples/scout/agent.py). The run still succeeds, the report is
still written — and the error scan finds it.

## Takeaways

- Four layers: **configuration**, **harness**, **model**, **runtime**. Check configuration
  first; it is cheapest and likeliest.
- **Three capabilities are silently absent unless asked for**: planning, skills, and files
  across runs. None errors.
- Triage: what tools did it have → what did it do → what did it produce → where did it think
  it was.
- **Checking `bound_tools` is the highest-value single check in this book.**
- **Read `ToolMessage`s, not conclusions.** Tool errors are returned, not raised, so the agent
  narrates confidently over a broken filesystem. Scan for `Error` first.
- **The file is the work; the final message is a summary.** They fail differently.
- An unchanged todo list is the clearest **stuck** signal.
- Subagent work is invisible by design — write files, stream with `subgraphs=True`, and
  suspect the brief.
- Reproduce by scripting the model *and* pinning the starting state, then **bisect by turning
  capabilities off one at a time**.

---

Previous: [Chapter 17 — Choosing models](17-choosing-models.md) ·
Next: [Chapter 19 — When it won't run](19-wont-run.md)
