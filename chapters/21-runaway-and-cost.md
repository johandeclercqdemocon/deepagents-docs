# Chapter 21 — Runaway agents and cost

Every other failure in this book costs time. This one costs money, and a deep agent is the
worst-placed of the four books' subjects to be careless about it: it is *designed* to take
many turns, so "it is still going" looks like it working.

## The default that is not a safety net

```
DEFAULT_RECURSION_LIMIT = 10007
```

Ten thousand supersteps before anything stops it. That is LangGraph's default (Chapter 5) and
it applies here unchanged.

For a chain that is a wasted second. For a deep agent — where each turn is a model call
carrying ~2,400 tokens of tool definitions plus the accumulated transcript — it is a bill you
will remember.

Set it:

```python
agent.invoke(payload, {"recursion_limit": 40})
```

```
GraphRecursionError: Recursion limit of 8 reached without hitting a stop condition.
```

A deep agent legitimately needs more turns than a simple one — 30 to 60 is a reasonable
ceiling for real work. That is still two orders of magnitude below the default.

## Three layers of defence

**1. `recursion_limit` on every invocation.** The crash barrier. It fails the run and discards
the work, which is why it should not be your primary control.

**2. A graceful cap.** `ModelCallLimitMiddleware` stops cleanly instead of raising:

```python
from langchain.agents.middleware import ModelCallLimitMiddleware

agent = create_deep_agent(model=model, middleware=[ModelCallLimitMiddleware(run_limit=30)])
```

```
completed with 5 model turns
```

The run *completed* — state intact, files written, checkpoint resumable. Compare a
`GraphRecursionError`, which loses everything.

Note `ToolCallLimitMiddleware` also exists, and its `exit_behavior` defaults to `"continue"`,
which blocks tool calls without stopping the loop. Pass `exit_behavior="end"` if you are using
it as a cost guard.

**3. A token budget.** Neither of the above knows about money. Count in middleware
(Chapter 14) and stop on spend, not turns — a turn with a 50 KB file read costs many times one
without.

## The harness overhead, measured

One `scout` run:

```
6 model turns
harness tool definitions: ~2414 tokens x 6 turns = ~14484 tokens of overhead
```

Fourteen thousand tokens of *tool definitions* for a six-turn investigation, before any
content. That is the harness's fixed cost, and it scales linearly with turns.

Two conclusions:

**Short tasks should not use a deep agent.** Chapter 1's rule, now with a number. A three-turn
task pays ~7,000 tokens for machinery it does not use.

**Long tasks should.** Those same tools are what stop four log files entering the transcript
and being re-sent forty times. The overhead is fixed per turn; the alternative grows
quadratically.

## Where the money actually goes

In order:

**The transcript, re-sent every turn.** Quadratic in run length. The filesystem is the fix,
and only if the agent uses it (Chapter 20).

**Tool definitions.** ~2,400 per turn, fixed. Add your own tools and a `response_format`
schema on top.

**Subagent calls.** Each is a fresh agent with its own system prompt and full tool
definitions. A subagent that saves 500 tokens of context costs more than it saves
(Chapter 9).

**Reading too much.** A `read_file` of a whole log is that log in the transcript, forever.

**Summarisation.** Costs a model call to save tokens later.

## Why agents run away

From the message list, which is where the answer always is:

- **The same tool call repeated with identical arguments** → the result does not permit
  stopping. `"Error: File not found"` invites another guess. Fix the tool output or the path.
- **Reading files it has already read** → context loss (Chapter 16).
- **No exit condition** → the prompt never said what "done" means. Say it.
- **Delegating in a loop** → a subagent returning something the parent cannot use, so it tries
  again.

## Noticing before the invoice

- **Record turns and tokens** in state or middleware, so cost is queryable per thread.
- **Alert on `GraphRecursionError`.** It should be zero; every occurrence already cost money.
- **Watch p99 turns per run**, not the mean — runaways hide in the tail.
- **Watch todo staleness.** An unchanged plan over many turns is the cheapest stuck-detector
  you have (Chapter 18).

## A pre-deploy checklist

- [ ] `recursion_limit` passed explicitly at every invoke site.
- [ ] A graceful cap via `ModelCallLimitMiddleware`.
- [ ] A token budget, if a single turn can read something large.
- [ ] Every tool returns something that permits stopping.
- [ ] The prompt defines "done".
- [ ] Subagents are used for large context savings, not tidiness.
- [ ] An alert on `GraphRecursionError` and on p99 turns.

## Try it

Watch the crash barrier, then the graceful cap:

```bash
uv run python -c "
from deepagents import create_deep_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from examples.scout.fakes import ScriptedModel

forever = [{'text':'again','tool_calls':[{'name':'ls','args':{'path':'/'}}]}]

try:
    create_deep_agent(model=ScriptedModel(script=forever)).invoke(
        {'messages':[{'role':'user','content':'go'}]}, {'recursion_limit': 8})
except Exception as e:
    print('crash barrier :', type(e).__name__)

out = create_deep_agent(model=ScriptedModel(script=forever),
                        middleware=[ModelCallLimitMiddleware(run_limit=4)]).invoke(
    {'messages':[{'role':'user','content':'go'}]}, {'recursion_limit': 50})
print('graceful cap  : completed with', sum(1 for m in out['messages'] if type(m).__name__=='AIMessage'), 'turns')
"
```

One raises and loses the run; one completes with state intact.

Then measure your own overhead:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
turns = sum(1 for m in out['messages'] if type(m).__name__ == 'AIMessage')
print(f'{turns} turns x ~2414 tokens of tool definitions = ~{2414*turns} tokens')
print('...before any content')
"
```

## Takeaways

- **The default recursion limit is 10007.** For an agent designed to take many turns, that is
  a bill, not a safety net. Set 30–60 explicitly.
- Three layers: **`recursion_limit`** (crash barrier, loses the run), **`ModelCallLimitMiddleware`**
  (stops gracefully, state intact), **a token budget** (the only one measuring money).
- `ToolCallLimitMiddleware` defaults to `exit_behavior="continue"`, which does **not** stop the
  loop.
- **Measured: ~14,500 tokens of tool definitions for a six-turn run.** Short tasks should not
  pay it; long tasks are exactly what it buys.
- Cost order: the re-sent transcript, tool definitions, subagent calls, over-reading,
  summarisation.
- Runaways are: a tool result that does not permit stopping, context loss, no defined "done",
  or a delegation loop.
- Record turns and tokens, alert on `GraphRecursionError` and p99 turns, and **watch for a
  todo list that has not changed**.

---

Previous: [Chapter 20 — When the agent does the wrong thing](20-wrong-thing.md) ·
Next: [Chapter 22 — Observing a long run](22-observing.md)
