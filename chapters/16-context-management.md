# Chapter 16 — Context management

The harness exists because context runs out. The filesystem and subagents keep bulk *out* of
the transcript; this chapter is about what to do with the transcript that accumulates anyway.

## Why it still grows

Even with perfect file discipline, a fifty-turn agent accumulates:

- Every tool call and its result — `grep` returned a path, `read_file` returned 200 lines.
- Every intermediate reasoning message.
- The task list, rewritten each time it changes.

And all of it is re-sent on every model call. Cost is quadratic in run length, and eventually
the window ends the run outright.

## The three levers, in order

**1. Read less.** The cheapest fix and the most neglected. `grep` before `read_file`; use
`offset`/`limit`; ask a subagent to read the big thing. Chapter 12's prompt lines are worth
more than any middleware here, because a token never read is a token never re-sent.

**2. Delegate.** Chapter 9, measured: the subagent's context did not join the parent's. For
anything that reads a lot and concludes briefly, this is the structural answer.

**3. Summarise.** When the run is genuinely long, compress old turns:

```python
from deepagents.middleware import SummarizationMiddleware
from deepagents.backends import StateBackend

SummarizationMiddleware(model=model, backend=StateBackend(), trigger=..., keep=...)
```

Note it takes a **`backend`** — deepagents' summarisation can write the summary into the
filesystem rather than only into the message list, so the detail is retrievable rather than
lost. That is the version worth having: a summary that says *"details in
/scratch/turns-1-20.md"* keeps the door open.

Check the signature on your installed version; this middleware's arguments have moved.

## What summarisation costs you

It is not free, and the losses are specific:

**Detail.** Whatever the summary omits is gone from the transcript. If the agent has not
written it to a file, it is gone entirely.

**A model call.** Summarising costs tokens too.

**Tool-call pairing.** A summary that splits an `AIMessage` with `tool_calls` from its
`ToolMessage` produces a malformed history that providers reject. Use the provided middleware
rather than trimming by hand.

The mitigation for the first is a prompt line from Chapter 12: **"write intermediate findings
to files as you go, not at the end."** Files survive summarisation; the transcript does not.

## What survives

Worth knowing precisely, because it tells you where to put things:

| | Survives summarisation |
|---|---|
| `files` | **yes** — it is state, not transcript |
| `todos` | **yes** — same |
| `messages` | compressed |
| `structured_response` | produced at the end, so unaffected |

This is the strongest argument for the todo list (Chapter 6): the plan is the one piece of
"where am I" that cannot be squeezed. An agent that has summarised away its history still
knows what remains.

And it is the strongest argument for writing files early. **The filesystem is your defence
against your own summariser.**

## Recognising the problem

Symptoms that mean context, not capability:

- The agent repeats work it already did — it forgot, and the evidence is gone.
- Quality degrades as the run goes on rather than being uniformly poor.
- It stops following the system prompt around turn thirty.
- A context-length error, which at least is honest.

The first is the reliable tell. An agent re-reading a file it read ten turns ago is telling
you its transcript no longer contains what it learned.

## Try it

Watch the transcript grow while the files stay small:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
msgs = sum(len(str(m.content)) for m in out['messages'])
files = sum(len(f['content']) for f in out['files'].values())
print(f'transcript: {msgs:6} chars across {len(out[\"messages\"])} messages')
print(f'files     : {files:6} chars across {len(out[\"files\"])} files')
print()
print('the transcript is re-sent every turn; the files are not')
"
```

Then check what a `read_file` result actually costs the transcript:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
for m in out['messages']:
    if type(m).__name__ == 'ToolMessage':
        print(f'{len(str(m.content)):5} chars  {str(m.content)[:48]!r}')
"
```

Every one of those numbers is paid again on every subsequent turn.

## Takeaways

- Even with good file discipline the transcript grows, and it is **re-sent every turn** — cost
  is quadratic in run length.
- Three levers in order: **read less**, **delegate**, **summarise**. The first is the cheapest
  and most neglected.
- `SummarizationMiddleware` takes a **backend**, so summaries can be written to files rather
  than only compressed into messages — keeping the detail retrievable.
- Summarisation costs detail, a model call, and can break tool-call pairing if done by hand.
- **`files` and `todos` survive summarisation; `messages` do not.** That is the case for the
  todo list, and for writing findings early.
- **The filesystem is your defence against your own summariser.**
- The reliable symptom is an agent **repeating work it already did**.

---

Previous: [Chapter 15 — Structured output](15-structured-output.md) ·
Next: [Chapter 17 — Choosing models](17-choosing-models.md)
