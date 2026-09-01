# Chapter 3 — The built-in tools

Eight tools arrive with every deep agent. They are the harness's whole surface area, so it is
worth knowing exactly what each returns — because what a tool returns is what the model
reasons from.

Every output below was produced by calling the tool.

## The filesystem seven

```
ls          -> ['/logs/', '/notes.md']
ls /logs    -> ['/logs/api.log']
read_file   -> '1  INFO start\n2  ERROR disk full\n3  WARN retry'
grep        -> '/logs/api.log'
glob        -> ['/logs/api.log']
edit_file   -> "Successfully replaced 1 instance(s) of the string in '/notes.md'"
write_file  -> 'Updated file /out.md'
delete      -> 'Deleted /notes.md'
```

**`ls(path)`** lists one directory. Note it takes a **required** `path` — there is no implicit
current directory, and calling it bare is an error. Directories come back with a trailing
slash.

**`read_file(file_path)`** returns the file with **line numbers prefixed**. That is deliberate:
numbered lines let the model refer to a specific line and let `edit_file` be precise. It also
means the content is not byte-identical to the file — if you are parsing a tool result in a
test, account for it.

`read_file` also takes `offset` and `limit` for reading part of a large file, which matters
when the whole point is keeping things out of the context window.

**`grep(pattern, path)`** returns **matching file paths, not matching lines**. This surprises
people: it is a file finder, not `grep -n`. The agent's normal move is `grep` to locate, then
`read_file` to see.

**`glob(pattern, path)`** finds files by name pattern — `**/*.log`.

**`write_file(file_path, content)`** creates or overwrites. Note the reply is *"Updated file"*
whether or not the file existed, so a model cannot tell from the result that it clobbered
something.

**`edit_file(file_path, old_string, new_string)`** replaces an exact string, and reports how
many instances it changed. Preferred over `write_file` for changing part of a file, because
it does not require the model to reproduce the whole thing.

**`delete(file_path)`** removes a file.

## `task` — the eighth

`task(description, subagent_type)` spawns a subagent with a **fresh context**, runs it, and
returns only its final answer. That is the context-isolation primitive from Chapter 1, and
Chapter 9 is about it.

## Errors are returned, not raised

```
read missing   -> "Error: File '/nope.md' not found"
ls no path     -> "Error invoking tool 'ls' with kwargs {}: path: Field required"
edit no match  -> "Error: String not found in file: 'zzz'"
```

All three come back as normal `ToolMessage`s. The agent sees the error and can react —
correct the path, try a different string, give up.

Two consequences:

**This is usually right.** A model that mistyped a path should retry, not crash the run.

**It can hide a broken system.** An agent whose every `read_file` fails looks like a model
having a bad day, and will keep paying for turns. Part IV covers spotting it; the short
version is to read the `ToolMessage`s, not just the final answer.

## What this means for your prompt

The tool descriptions already tell the model what these do — that is where the ~2,400 tokens
went. What they cannot tell it is **your conventions**:

- *Where* to write output. Left unsaid, the agent picks a filename, and it will not be the
  one you expected.
- Whether to `edit_file` or rewrite.
- What to do when a file is missing.

`scout`'s system prompt says *"write your conclusion to /findings.md"* for exactly this
reason. Chapter 12 goes further.

## The tools are ordinary LangChain tools

Nothing exotic: they are `BaseTool` instances with descriptions and argument schemas, bound
to the model like any other. So everything from the LangChain layer applies — `.args` shows
what the model sees, middleware can wrap them (Chapter 14), and `interrupt_on` can gate them
(Chapter 13).

The names are **fixed**. You cannot rename `write_file`, and prompting the model to use
`save_file` will produce a tool call that does not exist. If you need different semantics,
add your own tool alongside.

## Try it

Exercise the whole set against a seeded filesystem:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from examples.scout.fakes import ScriptedModel

seed = {'/logs/api.log': create_file_data('INFO start\nERROR disk full\nWARN retry\n')}
calls = [
    {'name':'ls','args':{'path':'/'}},
    {'name':'grep','args':{'pattern':'ERROR','path':'/'}},
    {'name':'read_file','args':{'file_path':'/logs/api.log'}},
]
model = ScriptedModel(script=[{'text':'x','tool_calls':[c]} for c in calls] + ['done'])
out = create_deep_agent(model=model).invoke({'messages':[{'role':'user','content':'go'}], 'files': seed})
for m in out['messages']:
    if type(m).__name__ == 'ToolMessage':
        print(repr(str(m.content))[:80])
"
```

Note that `grep` returned a **path**, and `read_file` returned **numbered lines**.

Then trigger the three errors and confirm they come back as tool results rather than
exceptions:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel
model = ScriptedModel(script=[{'text':'x','tool_calls':[{'name':'read_file','args':{'file_path':'/nope.md'}}]}, 'gave up'])
out = create_deep_agent(model=model).invoke({'messages':[{'role':'user','content':'go'}]})
for m in out['messages']:
    print(f'{type(m).__name__:13} {str(m.content)[:60]!r}')
"
```

The run succeeded. The failure is inside a `ToolMessage`.

## Takeaways

- Eight tools: seven filesystem operations and `task`.
- **`ls` requires an explicit `path`** — there is no current directory.
- **`read_file` returns line-numbered content**, not the raw file.
- **`grep` returns matching file paths, not matching lines.** It locates; `read_file` reads.
- `edit_file` replaces an exact string and reports the count — prefer it over rewriting a
  whole file.
- `write_file` says *"Updated file"* whether or not it overwrote something.
- **Tool errors come back as `ToolMessage`s, not exceptions.** Good for recovery, and it can
  hide a systematically broken setup while you keep paying for turns.
- Tool descriptions cover mechanics; **your prompt must cover conventions** — above all, where
  to write output.
- The names are fixed. Add tools alongside; do not try to rename these.

---

Previous: [Chapter 2 — Your first deep agent](02-first-agent.md) ·
Next: [Chapter 4 — State: files and messages](04-state.md)
