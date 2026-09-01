# Chapter 12 — Prompting a deep agent

Prompting an agent with a filesystem, a planner and delegation is different from prompting a
chat model, because you are not only describing a task — you are describing **how to use a
workspace**.

## You are not competing with a preamble

Chapter 2 measured it: with no skills configured, the harness's own system prompt is empty.

```
system prompt: 0 chars
with a system_prompt of your own: yours at position 0
```

Your prompt is the entire system prompt. The harness's guidance lives in the tool
descriptions instead — the ~2,400 tokens from Chapter 1.

Two consequences. You have the space, so use it. And **the model already knows what
`write_file` does** — do not waste words explaining the tools. Spend them on your conventions.

## The five things worth saying

`scout`'s prompt is short and every line is doing work:

```
You investigate production incidents.

Work from the files you are given. Read the logs, check the config against the
runbooks, and write your conclusion to /findings.md. Cite the file each claim
came from. If the evidence does not support a conclusion, say so.
```

**1. What the agent is for.** One line. It sets the frame everything else is read against.

**2. Where the input is.** *"the files you are given."* Better still, name the directories:
*"logs are in /logs, runbooks in /runbooks."* An agent that does not know where to look
starts with `ls /` and wastes turns.

**3. Where to write output — the highest-value line in the prompt.** Unsaid, the agent
invents a path and your `result["files"]["/findings.md"]` raises `KeyError`. Name every path
you intend to read.

**4. How to cite.** *"Cite the file each claim came from."* This is the single most effective
anti-fabrication instruction available: a claim that must carry a source is a claim the model
has to have actually seen. It is also how you audit the output afterwards.

**5. Permission to fail.** *"If the evidence does not support a conclusion, say so."* Without
it the agent produces a confident root cause for an incident whose logs it could not find.

## What to add for the harness's capabilities

Beyond the five, each capability wants a line — and none of them is on by default in the
sense of being *used well*.

**Planning.** *"Before you begin, write a plan with `write_todos`, and mark each item complete
as you finish it."* Chapter 6: the tool must also be enabled, and models often skip planning
unless asked.

**Reading narrowly.** *"Use `grep` to locate before reading. Read only the parts you need."*
Without this an agent reads whole files and you are back to the context problem the harness
was meant to solve.

**Delegation.** *"Delegate reading large files to the `log-reader` subagent."* Models
under-use `task` — it is unusual, and its benefit (context saved) is invisible to them.

**Durability.** With a `CompositeBackend`: *"Anything under /memories/ will be there next
time. Nothing else will."* The agent cannot otherwise know.

## Instructions live in three places

| Where | Loaded | For |
|---|---|---|
| System prompt | every call | who the agent is, where things go |
| Skill | on demand | a long procedure for one kind of task |
| A file the agent reads | when it reads it | reference material, project facts |

The mistake is putting a 40-line house style guide in the system prompt, where it is re-sent
on every turn of a fifty-turn task. That is a skill (Chapter 10).

The opposite mistake is putting *where to write output* in a skill. If it applies to every
run, it belongs in the prompt.

## Prompting the plan-execute cycle

Long agents drift. Three lines that measurably help:

**"Re-read your plan before each major step."** Counters the slow forgetting of what remains.

**"Write intermediate findings to files as you go, not at the end."** An agent that keeps
everything in its head until the final turn loses it to summarisation — and if the run fails
at turn thirty you have nothing.

**"State what you could not determine."** Turns a silent gap into a reportable one.

## Length

There is no fixed rule, but there is a shape: **short prompt, long skills.** The system prompt
is paid for on every turn; a fifty-turn task pays for it fifty times.

If your system prompt is over about thirty lines, look for the part that applies to only some
requests. That part is a skill.

## Try it

Look at what the model receives — your prompt, whole and alone:

```bash
uv run python -c "
from deepagents import create_deep_agent
from examples.scout.fakes import ScriptedModel
from examples.scout.agent import SYSTEM_PROMPT

seen = {}
class Spy(ScriptedModel):
    def _generate(self, messages, *a, **k):
        seen.setdefault('m', messages); return super()._generate(messages, *a, **k)

create_deep_agent(model=Spy(script=['ok']), system_prompt=SYSTEM_PROMPT).invoke(
    {'messages':[{'role':'user','content':'why did node-3 fail?'}]})
for m in seen['m']:
    print(f'--- {type(m).__name__}'); print(m.content)
"
```

Two messages: your prompt and the question. Nothing else.

Then delete *"write your conclusion to /findings.md"* from `SYSTEM_PROMPT` in
[`examples/scout/agent.py`](../examples/scout/agent.py) and consider what your reader code
would do — `result["files"]["/findings.md"]` has nothing to find.

## Takeaways

- **Your `system_prompt` is the whole system prompt** — the harness adds none. You have the
  space; do not spend it explaining tools the model already has descriptions for.
- Five lines earn their place: what the agent is for, **where the input is**, **where to write
  output**, **how to cite**, and **permission to fail**.
- "Write your conclusion to /findings.md" is the highest-value line — without it the agent
  invents a path and your reader raises `KeyError`.
- "Cite the file each claim came from" is the most effective anti-fabrication instruction, and
  makes the output auditable.
- Each capability wants a line: ask for a plan, ask it to `grep` before reading, ask it to
  delegate, and say which paths are durable.
- Three homes for instructions: **prompt** (always), **skill** (on demand), **file** (when
  read). A long style guide in the prompt is re-sent every turn.
- **Short prompt, long skills.** Over ~30 lines, something in there is a skill.

---

Previous: [Chapter 11 — Memory across sessions](11-memory.md) ·
Next: [Chapter 13 — Permissions and approval](13-permissions.md)
