# Chapter 10 — Skills

A skill is a folder with a `SKILL.md` in it. The agent is told the skill *exists* on every
call, and reads the contents only when it decides the skill applies.

That two-stage arrangement — advertise cheaply, load fully on demand — is called progressive
disclosure, and it is how you give an agent a large body of instructions without paying for
all of it every turn.

## The shape

```
examples/scout/skills/
└── incident-report/
    └── SKILL.md
```

```markdown
---
name: incident-report
description: House format for writing a post-incident findings report, with the required sections and the citation rule
---

# Incident report format

## When to use

When writing anything to `/findings.md` or any file the incident review will read.

## Instructions

Use exactly these sections, in this order:
1. `# <node> outage` — one line stating the root cause.
2. `## Evidence` — a bullet per fact, each ending with `[source]`.
...
```

The frontmatter is **required**. `name` and `description` are what the agent sees up front;
the body is what it reads if it decides to.

## Wiring it up

Skills need a backend that can read them:

```python
agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=str(SKILLS_ROOT), virtual_mode=True),
    skills=["./skills/"],
)
```

`skills=["./skills/"]` alone does nothing — there is no filesystem to read from by default
(Chapter 8). This is the most common reason a skill silently fails to appear.

## What the agent actually sees

The tool list does **not** change:

```
tools offered: ['ls', 'read_file', 'write_file', 'edit_file', 'delete', 'glob', 'grep', 'task']
```

Skills are not tools. They arrive in the **system prompt** — the same prompt Chapter 2
measured as empty without them:

```
## Skills System

You have access to a skills library that provides specialized capabilities and domain knowledge.

**Available Skills:**

- **incident-report**: House format for writing a post-incident findings report, with the
  required sections and the citation ...
```

So the per-call cost is **one line per skill**: its name and description. The body is only
read if the agent opens the file — with `read_file`, using the tools it already has.

That is the whole mechanism, and knowing it tells you where to spend effort.

## The description is the entire routing decision

The agent chooses using the description alone. It has not read the skill. So:

**Say when to use it, not what it is.** *"House format for writing a post-incident findings
report"* beats *"Reporting helper"*. `scout`'s description names the trigger — writing to
`/findings.md`.

**Be specific.** Vague descriptions produce skills that never load, or load for everything.

**Make them distinguishable.** Two skills with overlapping descriptions is a coin flip.

A skill that never loads is nearly always a description problem, not a content problem —
and it fails silently, because nothing reports "considered and rejected".

## Skills versus the system prompt versus memory

Three places instructions can live, and the choice is about cost and scope:

| | Loaded | Cost | Use for |
|---|---|---|---|
| **System prompt** | always | every call | who the agent is; where to write |
| **Skill** | on demand | one line per call | long, task-specific procedure |
| **Memory file** | when read | nothing until read | facts about this user or project |

The rule: **if it applies to every request, it belongs in the system prompt. If it applies to
one kind of request and is long, it is a skill.**

A 40-line house style guide for reports is a skill. "Cite your sources" is a system prompt
line.

## What skills are good for

**House formats.** Exactly the example above.

**Procedures with steps.** A runbook the agent should follow rather than improvise.

**Domain knowledge too long for a prompt.** Reference material consulted occasionally.

**Things that change independently of your code.** A skill is a file; editing it does not
require a deploy — which is also a governance question, since it means prompt-shaped content
lives outside code review unless you put it in the repository.

## What they are not

**Not tools.** A skill cannot *do* anything. It is instructions. If the agent needs an action,
write a tool.

**Not enforced.** The agent may read the skill and ignore it, or not read it at all.

**Not inherited by subagents.** A subagent gets the skills you give *it*:

```python
create_deep_agent(
    skills=["./skills/"],
    subagents=[{"name": "writer", "skills": ["./skills/"], ...}],   # explicitly
)
```

Forgetting this produces a subagent that ignores the house format while the parent obeys it —
a confusing bug, because the skill demonstrably works.

## Try it

See a skill advertised in the system prompt without appearing as a tool:

```bash
uv run python -c "
import pathlib
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from examples.scout.fakes import ScriptedModel

seen = {}
class Spy(ScriptedModel):
    def _generate(self, messages, *a, **k):
        seen.setdefault('m', messages); return super()._generate(messages, *a, **k)

def text(msg):
    c = msg.content
    return c if isinstance(c, str) else ''.join(b.get('text','') for b in c if isinstance(b, dict))

root = pathlib.Path('examples/scout').resolve()
model = Spy(script=['ok'])
create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(root), virtual_mode=True),
                  skills=['./skills/']).invoke({'messages':[{'role':'user','content':'write findings'}]})
prompt = chr(10).join(text(m) for m in seen['m'])
print('tools        :', model.bound_tools)
print('in prompt    :', 'incident-report' in prompt)
i = prompt.find('Available Skills')
print(prompt[i:i+220])
"
```

The skill is in the prompt; the tool list is unchanged.

Then remove the `backend=` argument and confirm the skill vanishes — silently.

## Takeaways

- A skill is a folder with a `SKILL.md` and **required frontmatter** (`name`, `description`).
- **Skills need a backend that can read them.** `skills=[...]` alone silently does nothing.
- They are **not tools**. They appear in the **system prompt** as one line each; the body is
  read on demand with `read_file`.
- So the per-call cost is one line per skill — that is the whole point.
- **The description is the entire routing decision.** Say when to use it, be specific, keep
  them distinguishable. A skill that never loads is a description problem, and it fails
  silently.
- System prompt for what applies always; skill for long, task-specific procedure; memory for
  facts about this user or project.
- Skills are not enforced, and **not inherited by subagents** — pass them explicitly.

---

Previous: [Chapter 9 — Subagents](09-subagents.md) ·
Next: [Chapter 11 — Memory across sessions](11-memory.md)
