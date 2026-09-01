# Chapter 17 — Choosing models

A deep agent makes many model calls — one per turn, plus one per subagent turn. That changes
the economics of model choice from "which is best" to "which is best *where*", and it is the
easiest large saving available.

## One model is a default, not a requirement

```python
agent = create_deep_agent(model=model, subagents=[
    {"name": "log-reader", "description": "...", "system_prompt": "...", "model": small_model},
])
```

The parent and each subagent can have their own. That matters because the work is genuinely
different:

**The parent judges.** It decides what to investigate, whether the evidence supports a
conclusion, and when to stop. This is where a capable model earns its price.

**Subagents grind.** Read a file, summarise it, report one line. Constrained, mechanical, and
frequently the majority of your calls.

Putting a small model on the grinding and a large one on the judging is usually the single
biggest cost reduction available in a deep agent — and because the subagent's brief is narrow
(Chapter 9), the quality risk is small.

## What the parent model needs to be good at

Not general capability so much as three specific things:

**Long-context coherence.** Twenty turns in, does it still remember the task? This is what
separates models on long agentic work and it does not show up in short benchmarks.

**Tool discipline.** Choosing correctly among eight built-in tools plus yours, with sensible
arguments. A model that reaches for `write_file` when it should `edit_file`, or ignores
`grep`, will burn context.

**Knowing when to stop.** Agents that cannot decide they are finished are the expensive
failure of Chapter 20.

## Setting them

```python
agent = create_deep_agent(model="claude-sonnet-5", tools=TOOLS)
```

or an instance, which is what you want in a real project (Chapter 24):

```python
def parent_model():
    return init_chat_model(os.environ["PARENT_MODEL"], temperature=0, timeout=60, max_retries=0)
```

> **Running any of this costs money.** Every example in this book uses `ScriptedModel`, which
> does not.

`temperature=0` is worth defaulting to. An investigation is not a creative task, and
determinism makes failures reproducible — which Part IV depends on.

## Testing without a model at all

The book's `ScriptedModel` replays fixed replies with real tool calls, so the harness drives
it exactly as it would drive Claude. That is how every output here is reproducible, and it is
how Chapter 25 tests the agent for free.

The one non-obvious requirement, learned the hard way:

> `bind_tools` must return `self`, not a copy. The harness re-binds tools on every step; a copy
> gets a fresh script cursor and restarts from entry 0 every turn. If entry 0 calls a tool,
> that is an infinite loop that only stops at the recursion limit.

Sixty lines, in [`examples/scout/fakes.py`](../examples/scout/fakes.py), and worth writing for
your own project.

## Fallbacks and retries

Both come from the LangChain layer:

```python
model = primary.with_fallbacks([backup])       # provider outage
model = model.with_retry(stop_after_attempt=3) # transient failures
```

Fallbacks fire on exceptions, not bad answers. And **do not stack retries** — client-level
retries under these multiply, so three under three is nine calls before anything is reported.

On a long agent this matters more than on a single call: a transient failure at turn forty
loses the whole run unless something absorbs it, so a retry on the model is worth having.
Pair it with a checkpointer (Chapter 4) so a genuine crash can resume rather than restart.

## Try it

Give a subagent its own model and confirm the parent's is untouched:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel

parent = ScriptedModel(script=[
    {'text':'delegating','tool_calls':[{'name':'task','args':{'description':'read the log','subagent_type':'reader'}}]},
    'parent concluded'])
child = ScriptedModel(script=['child answered'])

sub = {'name':'reader','description':'Reads a log.','system_prompt':'Report one line.','model':child}
out = create_deep_agent(model=parent, subagents=[sub]).invoke({'messages':[{'role':'user','content':'go'}]})
for m in out['messages']:
    print(f'  {type(m).__name__:13} {str(m.content)[:44]!r}')
print()
print('parent model calls:', parent.calls, '| child model calls:', child.calls)
"
```

Two models, each used where it belongs.

## Takeaways

- A deep agent makes many calls, so model choice becomes **which model where**.
- **A small model for subagents and a large one for the parent** is usually the biggest saving
  available, and the risk is small because subagent briefs are narrow.
- The parent needs **long-context coherence**, **tool discipline**, and **knowing when to
  stop** — none of which short benchmarks measure.
- Default to `temperature=0`: an investigation is not creative, and determinism makes failures
  reproducible.
- Construct models in one function so they are configuration and tests can inject a fake.
- A scripted model's **`bind_tools` must return `self`**, or the harness's per-step re-binding
  restarts the script and loops forever.
- Retries matter more here than on a single call — a failure at turn forty loses the run.
  Do not stack them, and pair with a checkpointer so crashes resume.

---

Previous: [Chapter 16 — Context management](16-context-management.md) ·
Next: [Chapter 18 — The debugging mindset](18-debugging-mindset.md)
