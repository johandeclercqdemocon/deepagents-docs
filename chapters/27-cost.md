# Chapter 27 — Cost and context

A deep agent is the most expensive shape in these five books, and the cost is structural
rather than accidental: many turns, each carrying a growing transcript and a fixed block of
tool definitions.

Chapter 21 covered runaway failures. This chapter is about the cost of an agent working
*correctly*.

## The fixed cost, measured

The harness's tool definitions, per call:

```
ls             345 chars      read_file     1685 chars
write_file     622 chars      edit_file     1012 chars
delete         512 chars      glob          1526 chars
grep          2254 chars      task          1700 chars
TOTAL         9656 chars  (~2414 tokens, on every call)
```

For one `scout` run:

```
6 model turns
~2414 tokens x 6 turns = ~14484 tokens of overhead
```

**Fourteen thousand tokens of machinery for a six-turn investigation**, before any content.

Add your own tools and a `response_format` schema on top, and note it is charged again inside
every subagent — a subagent call is a fresh agent with the full block.

## When that is worth paying

The overhead is **linear in turns**. The alternative — everything in the transcript — is
**quadratic in work**.

So the arithmetic flips at a scale you can reason about:

**Short tasks lose.** A three-turn task pays ~7,000 tokens for a filesystem it barely uses.
Chapter 1's rule, with a number: use `create_agent`.

**Long tasks win, decisively.** Four log files read and re-sent across forty turns is far more
than 2,400 × 40. The harness's whole value is converting a quadratic into a linear.

The break-even is roughly where the material the agent must consult exceeds what you are happy
re-sending every turn. In practice: **if the agent reads files, it wants the harness; if it
only calls APIs and returns short results, it does not.**

## Where the money goes

In order:

**1. The transcript, re-sent every turn.** Quadratic, and the thing the filesystem exists to
prevent — but only if the agent uses it. An agent that `read_file`s whole logs has the cost
*and* the overhead.

**2. Tool definitions.** ~2,400 per turn, fixed, plus yours.

**3. Subagent calls.** Each pays the full block again. Chapter 9's rule: delegate for large
context savings, not tidiness.

**4. Reading too much.** One 50 KB log read is 50 KB in every subsequent turn.

**5. Summarisation.** A model call to save later calls.

## The levers, in order

**Read less.** `grep` before `read_file`; `offset`/`limit`; delegate the big reads. Prompting
(Chapter 12) is cheaper than any middleware here, because a token never read is never re-sent.

**Delegate the bulky.** Measured in Chapter 9: the subagent's context did not join the
parent's.

**A small model for subagents.** Chapter 17. Subagent turns are often the majority, and their
briefs are narrow.

**Cap turns.** `ModelCallLimitMiddleware(run_limit=30)`. A wandering agent is a linear cost in
turns and a quadratic one in transcript.

**Summarise, last.** It costs a call and loses detail; do it when the run genuinely is long.

**Trim the toolset.** You cannot remove the built-ins — but you can avoid adding twelve of
your own. Every tool is in every call, and `LLMToolSelectorMiddleware` exists for when there
are too many.

## Measuring it

Token counts are on the message:

```python
sum((m.usage_metadata or {}).get("total_tokens", 0)
    for m in result["messages"] if hasattr(m, "usage_metadata"))
```

Two habits:

- **Track cost per run, not per token.** A cheaper model that needs twice the turns is not
  cheaper.
- **Track turns as the leading indicator.** Tokens follow turns, and turns are visible
  earlier — you can stop a run at turn fifty; you cannot un-spend the tokens.

`scout`'s scripted model returns fixed counts (100 in, 20 out) precisely so this arithmetic is
reproducible offline.

## An illustrative comparison

An investigation agent over 1,000 incidents a month, at roughly $3 per million input tokens:

| Approach | Turns | Input tokens/incident | Monthly |
|---|---|---|---|
| No filesystem, everything in transcript | 12 | ~180,000 | ~$540 |
| Harness, agent reads whole files | 12 | ~90,000 | ~$270 |
| Harness, `grep`-then-read, big reads delegated | 10 | ~40,000 | ~$120 |
| Plus a small model for subagents | 10 | ~40,000 | ~$70 |

The token counts are illustrative — your incidents are not these incidents. **The ratios are
the point**, and the two largest levers are *how much the agent reads* and *which model does
the reading*. Neither is a library feature; both are available on day one.

## Try it

Measure the overhead against the content on a real run:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
turns = sum(1 for m in out['messages'] if type(m).__name__ == 'AIMessage')
content = sum(len(str(m.content)) for m in out['messages'])
print(f'{turns} turns')
print(f'overhead : ~{2414*turns} tokens of tool definitions')
print(f'content  : ~{content//4} tokens of transcript')
"
```

Then find the expensive tool results — the ones re-sent on every later turn:

```bash
uv run python -c "
from examples.scout.agent import investigate
for m in investigate()['messages']:
    if type(m).__name__ == 'ToolMessage':
        n = len(str(m.content))
        print(f'{n:5} chars{\"   <- re-sent every later turn\" if n > 400 else \"\"}')
"
```

## Takeaways

- Measured: **~2,414 tokens of tool definitions per call**, ~14,500 for a six-turn run, before
  any content — and charged again inside every subagent.
- The overhead is **linear in turns**; the alternative is **quadratic in work**. That is the
  whole trade.
- **If the agent reads files, the harness pays for itself. If it only calls APIs and returns
  short results, it does not.**
- Cost order: the re-sent transcript, tool definitions, subagent calls, over-reading,
  summarisation.
- Levers in order: **read less**, **delegate the bulky**, **a small model for subagents**,
  **cap turns**, summarise last, and do not add twelve tools of your own.
- Track **cost per run**, and **turns as the leading indicator** — you can stop a run, you
  cannot un-spend tokens.
- The two biggest levers are how much the agent reads and which model reads it.

---

Previous: [Chapter 26 — Evaluating a deep agent](26-evaluation.md) ·
Next: [Chapter 28 — Security](28-security.md)
