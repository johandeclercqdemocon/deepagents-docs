# Chapter 7 — The virtual filesystem

The central capability. Chapter 4 covered where files live; this chapter is about using them
well, because a filesystem the agent ignores buys you nothing.

## The point, restated

Without a filesystem, everything the agent reads stays in the message list forever. With one,
the agent reads what it needs, writes what it concludes, and the transcript stays small.

For `scout`, that is the difference between carrying four log files through every turn and
carrying a sentence.

```
files afterwards:
  /config/limits.yaml
  /findings.md          <- written by the agent
  /logs/api.log
  /logs/media.log
  /runbooks/disk.md
```

Four files in, one file out. The report is the deliverable; the logs never entered the
conversation whole.

## Seeding the workspace

Files go in as input:

```python
from deepagents.backends.utils import create_file_data

agent.invoke({
    "messages": [{"role": "user", "content": "why did node-3 fail?"}],
    "files": {
        "/logs/api.log": create_file_data("...log text..."),
        "/runbooks/disk.md": create_file_data("...runbook..."),
    },
})
```

This is how documents reach the agent, and it is better than pasting them into the prompt for
the obvious reason: **the agent decides what to read.** A 200 KB log costs nothing until it is
opened, and `grep` may mean it never is.

`scout` seeds four files this way — see
[`examples/scout/workspace.py`](../examples/scout/workspace.py).

## The read-and-write cycle

The pattern that works, and the one to prompt for:

1. **Locate** — `grep` or `glob` to find the file. Cheap: returns paths, not content.
2. **Read narrowly** — `read_file` with `offset`/`limit` if it is large.
3. **Write conclusions** — `write_file` to a named path.
4. **Refine** — `edit_file` rather than rewriting.

`scout` does exactly this: `grep ERROR /logs` → `read_file /runbooks/disk.md` →
`write_file /findings.md`.

The failure to avoid is an agent that reads whole files it does not need. That is the original
context problem with extra steps, and the fix is prompting: *"Use grep to locate before
reading. Read only the parts you need."*

## Files as the interface

Once the agent has a filesystem, files become how you communicate with it in both directions.

**In:** documents, logs, prior output, configuration.

**Out:** the deliverable. `result["files"]["/findings.md"]["content"]` is what you ship.

**Between turns:** the agent's own notes. A long investigation can write `/scratch/notes.md`
and re-read it after summarisation has eaten the transcript.

**Between agents:** a subagent writes a file; the parent reads it (Chapter 9).

That last one is the pattern worth internalising: **files are how subagents return more than a
sentence.**

## Tell it where to write

The single highest-value line in a deep agent's system prompt:

```
write your conclusion to /findings.md
```

Without it the agent invents a path — `report.md`, `/output/findings.txt`, `/tmp/analysis.md`
— and your code that reads `result["files"]["/findings.md"]` gets a `KeyError`. It is not the
agent's fault; you did not say.

Name the paths you will read. If there are several, list them.

## Paths

Two things measured in Chapter 3 that matter here:

**Everything is absolute.** `write_file("notes.md", ...)` stores `/notes.md`. If your code
looks for `"notes.md"`, it will not find it.

**`ls` needs an explicit path.** There is no working directory.

A useful convention is directories by role — `/logs/`, `/runbooks/`, `/findings.md` — because
the agent reasons about paths as names. A flat pile of files with unclear names produces
worse `grep` behaviour than a small tree with obvious ones.

## The size problem

Files keep bulk out of the *message list*, not out of the *state*. Everything in `files` is
checkpointed on every superstep. Seed a 50 MB log and you are writing 50 MB per checkpoint.

For genuinely large inputs, use a backend that does not live in state — `FilesystemBackend`
for real files, `StoreBackend` for a database. Chapter 8 covers the trade, and Chapter 27
measures the cost.

## Try it

Watch the workspace go in and the deliverable come out:

```bash
uv run python -c "
from examples.scout.agent import investigate
from examples.scout.workspace import seed

print('in :', sorted(seed()))
out = investigate()
print('out:', sorted(out['files']))
print()
print(out['files']['/findings.md']['content'])
"
```

Then confirm the logs never entered the conversation whole — the agent grepped instead:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
for m in out['messages']:
    if type(m).__name__ == 'ToolMessage':
        print(f'{len(str(m.content)):5} chars  {str(m.content)[:52]!r}')
"
```

Compare those lengths against the size of the files in `workspace.py`.

## Takeaways

- The filesystem exists so the agent's **working area is not its message list**.
- Seed files as input with `create_file_data`; the agent then decides what to read, so a large
  document costs nothing until opened.
- The cycle is **locate (`grep`/`glob`) → read narrowly → write conclusions → refine with
  `edit_file`**. Prompt for it, or the agent reads whole files it does not need.
- Files are the interface in every direction: input, deliverable, the agent's own notes across
  summarisation, and **how subagents return more than a sentence**.
- **Tell the agent where to write.** Unsaid, it invents a path and your reader gets a
  `KeyError`.
- Paths are absolute; `ls` needs an explicit one. Organise by role so names are meaningful.
- Files keep bulk out of the context but **not out of the checkpoint**. Large inputs want a
  different backend (Chapter 8).

---

Previous: [Chapter 6 — Planning](06-planning.md) ·
Next: [Chapter 8 — Backends](08-backends.md)
