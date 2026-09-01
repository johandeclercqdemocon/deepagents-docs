# Chapter 20 — When the agent does the wrong thing

Layers 2 and 3. It ran, the capabilities are present, and the behaviour is wrong. This is
where people reach for prompt engineering, and where being disciplined about *what* is broken
saves days.

## Symptom → cause

### It never plans

Check `write_todos` is offered at all (Chapter 6) — that is the answer more often than not.
If it is present and unused, the prompt does not ask. Models start work rather than plan
unless told: *"Before you begin, write a plan with `write_todos`."*

### It plans once and never updates

The list is stale, which is worse than no list because it looks like progress. Ask explicitly:
*"Mark each item complete as you finish it."*

### It reads whole files it does not need

The original context problem, back again. The agent has `grep` and does not use it. Prompt:
*"Use `grep` to locate before reading. Read only the parts you need."*

Symptom to look for: `ToolMessage`s of several thousand characters. Chapter 16's exercise
measures them.

### It writes to the wrong path

You did not say where. Chapter 12's highest-value line. Name every path you will read.

### It never delegates

`task` is unusual and its benefit — context saved — is invisible to the model. Name the
subagent and the trigger: *"Delegate reading any file over 100 lines to `log-reader`."*

### The subagent's answer is useless

Suspect the `description` before the subagent. It is the entire brief and there is no
follow-up (Chapter 9). `"read the log"` produces what you would expect; `"report the first
ERROR line with its timestamp, or say none found"` produces something usable.

### It fabricates a conclusion

Two different bugs:

- **The evidence was not there.** It could not find the file, and the prompt did not permit
  failing. Add *"If the evidence does not support a conclusion, say so"* — and check the tool
  errors, because a missing file is usually why.
- **The evidence was there and it misread it.** A model problem. Chapter 17: a more capable
  parent model, or decompose the step.

Requiring citations distinguishes them: a claim the agent cannot attribute is one it invented.

### It repeats work it already did

Context, not capability. It forgot, and the transcript no longer holds what it learned
(Chapter 16). Write findings to files earlier.

### It stops too early

Often the exit condition is implicit. Say what "done" means: *"You are finished when
/findings.md exists and every todo is complete."*

### It ignores a skill

The description, not the content (Chapter 10). And check the skill is loaded at all — no
backend means no skill, silently.

## The test that halves the problem

Give the agent the right context by hand and see whether it reasons well:

```python
agent.invoke({
    "messages": [{"role": "user", "content": "why did node-3 fail?"}],
    "files": {"/logs/api.log": create_file_data("...the one relevant log...")},
})
```

If it concludes correctly from a curated workspace but not from the real one, the problem is
**finding** — search, prompting, delegation. If it still gets it wrong, the problem is
**reasoning** — model or prompt.

That single split is worth more than any amount of staring at transcripts.

## Prompt changes are code changes

With no type checker and side effects you will not see:

**Change one thing at a time.** Two changes and an improvement tells you nothing.

**Keep the case you were fixing**, as a test (Chapter 25).

**Re-check the cases that used to work.** Prompt changes regress silently — a line that makes
the agent delegate more can make it stop reading things it should.

**Version prompts with your code.** A prompt edited in a database is an unreproducible
deployment.

## When it is the model

Signals that no prompt will fix:

- It gets it right with a larger model and the identical prompt and files.
- It loses coherence past a certain run length regardless of instruction.
- It cannot choose among tools sensibly — reaching for `write_file` where `edit_file` was
  obvious.

Then: a more capable parent model (Chapter 17), or decompose the task so each step is one the
model can do.

## Try it

Run the split — same question, curated workspace:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from examples.scout.fakes import ScriptedModel

script = [{'text':'reading','tool_calls':[{'name':'read_file','args':{'file_path':'/logs/api.log'}}]},
          'Root cause: disk exhaustion.']
out = create_deep_agent(model=ScriptedModel(script=script)).invoke({
    'messages':[{'role':'user','content':'why did node-3 fail?'}],
    'files': {'/logs/api.log': create_file_data('ERROR write failed: no space left on device')}})
print(out['messages'][-1].content)
"
```

Right answer from a curated workspace means your bug is finding, not reasoning.

Then look for oversized tool results, the tell for an agent reading too much:

```bash
uv run python -c "
from examples.scout.agent import investigate
for m in investigate()['messages']:
    if type(m).__name__ == 'ToolMessage':
        n = len(str(m.content))
        print(f'{n:5} chars {\"  <- large\" if n > 500 else \"\"}')
"
```

## Takeaways

- Check the capability exists before debugging behaviour around it. "It never plans" is
  usually a missing `TodoListMiddleware`.
- Most behavioural fixes are **prompt lines**: ask for a plan, ask it to be updated, ask for
  `grep` before reading, name the output path, name the delegation trigger, define "done".
- **A useless subagent answer is usually an underspecified `description`.**
- Fabrication is two bugs: **missing evidence** (check tool errors, permit failure) or
  **misread evidence** (a model problem). **Citations distinguish them.**
- Repeated work means context loss — write findings to files earlier.
- **Curate the workspace by hand.** Right answer means your bug is *finding*; wrong answer
  means *reasoning*. That split halves the search.
- Prompt changes are code changes: one at a time, keep the case, re-check what worked, and
  version them with your code.

---

Previous: [Chapter 19 — When it won't run](19-wont-run.md) ·
Next: [Chapter 21 — Runaway agents and cost](21-runaway-and-cost.md)
