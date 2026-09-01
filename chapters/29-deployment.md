# Chapter 29 — Deployment

A deep agent runs for minutes, writes files, and may pause for a human. None of those fit a
synchronous HTTP request, so deployment is mostly about accepting that it is a **job**, not a
call.

## It is a job

```python
@app.post("/investigate")
async def start(req: Request):
    thread_id = f"incident-{req.incident_id}"
    queue.enqueue(run_investigation, thread_id, req.question)
    return {"thread_id": thread_id, "status": "running"}

@app.get("/investigate/{thread_id}")
async def poll(thread_id: str):
    snap = app.state.agent.get_state({"configurable": {"thread_id": thread_id}})
    return {
        "status": "paused" if snap.interrupts else ("running" if snap.next else "done"),
        "progress": snap.values.get("todos", []),
        "files": sorted(snap.values.get("files", {})),
    }
```

Two things this gets right beyond being async. The **poll endpoint reads state directly** —
no bookkeeping of your own, because the checkpointer already has it. And it returns
**progress**, which for a minutes-long agent is what a caller actually wants (Chapter 22).

## The three storage decisions

| | Development | Production |
|---|---|---|
| Checkpointer | `InMemorySaver` | **Postgres** |
| Store (if used) | `InMemoryStore` | **Postgres** |
| Backend | `StateBackend` | `StateBackend`, or `CompositeBackend` routing durable paths |

**The moment you run two workers, in-memory anything is wrong.** A job started on worker 1 and
polled on worker 2 finds nothing; an approval issued to worker 3 cannot resume a thread worker
1 paused.

Remember `await checkpointer.setup()` at startup to create the tables.

## Resuming after a crash

The payoff for having a checkpointer. A crashed run is not lost:

```python
snap = agent.get_state(config)
if snap.next and not snap.interrupts:
    agent.invoke(None, config)      # continue from where it stopped
```

`invoke(None, config)` means "no new input, resume". This is LangGraph's (Chapter 5), and it
matters more here than anywhere else in these books: a deep agent forty turns into an
investigation represents real money, and restarting from scratch spends it again.

A sweeper over threads with a non-empty `next`, no pending interrupt, and no recent activity is
a small amount of code and is what makes durability operational rather than theoretical.

Two caveats. Nodes must be **idempotent** — a resumed superstep re-runs in full, so a tool
that sends email needs a guard. And a resumed thread runs against **today's code**.

## The deploy hazard

A thread paused for approval on Monday resumes on Wednesday, against Wednesday's code. The
checkpoint holds state, not your agent.

Specific to this layer:

- **Renaming a subagent** breaks threads mid-delegation.
- **Changing the state schema** breaks threads mid-flight.
- **Changing the system prompt** silently changes behaviour halfway through an investigation —
  the first half was done under different instructions.
- **Removing a tool** the agent was about to call.

None is reported as a deploy failure. It shows up as a few stuck or strange threads a day
later.

Working with it: treat subagent names and the state schema as a public interface; drain
in-flight threads before structural changes; and for a genuinely incompatible change, run the
new version alongside and let the old drain.

## Where files go

The question the other books do not have. `result["files"]` is the deliverable, and it lives
in the checkpoint by default — which is fine for a report and wrong for anything large or
long-lived.

Decide explicitly:

- **Keep in state** — simple, and every file is in every checkpoint (Chapter 27).
- **Extract on completion** — read `result["files"]` and write to object storage. Usually right
  for artefacts anyone will look at later.
- **Route durable paths to a Store** — `CompositeBackend`, so `/memories/` persists and scratch
  does not (Chapter 11).

Whatever you choose, **prune finished threads**. Checkpoints accumulate per superstep, per
thread, forever, and a deep agent produces many supersteps. This is both a cost control and a
privacy one, and it is the operational task most often missing.

## An operational checklist

- [ ] Postgres checkpointer, with `setup()` called at startup.
- [ ] Agent built **once** at startup, not per request.
- [ ] `recursion_limit` and a call limit at every invoke site (Chapter 21).
- [ ] Runs as jobs with a `thread_id`, not synchronous requests.
- [ ] A poll endpoint reading `get_state` — status, todos, files.
- [ ] A sweeper for crashed threads (non-empty `next`, no interrupt).
- [ ] A monitor for interrupt age, if using approval.
- [ ] Artefacts extracted or routed deliberately; **checkpoint retention policy**.
- [ ] Subagent names and state schema reviewed for live-thread compatibility.
- [ ] Backend and `root_dir` reviewed as a security boundary (Chapter 28).

## Try it

Poll a run the way a deployment would:

```bash
uv run python -c "
from langgraph.checkpoint.memory import InMemorySaver
from examples.scout.agent import build
from examples.scout.workspace import seed

agent = build(checkpointer=InMemorySaver())
cfg = {'configurable': {'thread_id': 'incident-4471'}}
agent.invoke({'messages':[{'role':'user','content':'why did node-3 fail?'}], 'files': seed()},
             cfg, )

snap = agent.get_state(cfg)
print('status  :', 'paused' if snap.interrupts else ('running' if snap.next else 'done'))
print('progress:', [t['status'] for t in snap.values.get('todos', [])])
print('files   :', sorted(snap.values.get('files', {})))
"
```

Everything a status endpoint needs, from the checkpointer, without you storing anything.

## Takeaways

- A deep agent is a **job**, not a request. Return a `thread_id`; let the caller poll.
- **The poll endpoint reads `get_state` directly** — status, todos and files are already
  there, so keep no bookkeeping of your own.
- **Two workers means Postgres.** In-memory checkpointers break polling, approval and resume.
- `invoke(None, config)` resumes a crashed run — worth more here than anywhere, since forty
  turns is real money. Needs idempotent tools.
- **Resumed threads run against today's code.** Renaming a subagent, changing the state schema
  or editing the system prompt all break or silently alter in-flight threads.
- Decide where artefacts live — state, object storage, or a routed Store — and **prune
  finished threads**. Deep agents produce many checkpoints.

---

Previous: [Chapter 28 — Security](28-security.md) ·
Next: [Chapter 30 — Patterns](30-patterns.md)
