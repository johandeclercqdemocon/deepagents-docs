# Chapter 9 — Subagents

The `task` tool spawns a fresh agent, runs it, and returns only its answer. That is the
harness's second answer to the context problem, and the one people underuse.

## Context isolation, measured

Count the messages each model call receives across a delegation:

```
messages seen per model call: [2, 2, 4]
```

- **Call 1** — the parent: system prompt plus the user's question.
- **Call 2** — the **subagent**: two messages. A *fresh* context. It did not inherit the
  parent's history.
- **Call 3** — the parent again: its own transcript, plus the result.

And the parent's transcript afterwards:

```
HumanMessage  'investigate'
AIMessage     'delegating'
ToolMessage   'sub: disk full at 09:41'
AIMessage     'parent: root cause is disk'
```

The subagent read a file and reasoned about it. **None of that is in the parent's context** —
only the one-line conclusion. That is the whole feature:

> **A subagent spends context you do not pay for afterwards.**

## Defining one

```python
sub = {
    "name": "log-reader",
    "description": "Reads a log file and reports the single most significant line.",
    "system_prompt": "You read logs. Report one line, with its timestamp.",
}

agent = create_deep_agent(model=model, subagents=[sub])
```

The model then calls:

```python
task(description="summarise /logs/api.log", subagent_type="log-reader")
```

**The `description` is the prompt.** It is what the parent decides to say, and it is the whole
brief — the subagent cannot ask a follow-up. A vague `description` produces a vague answer,
and the parent has no way to know it was vague.

Subagents can have their own `tools` and their own `model`. A cheap model for bulk reading and
an expensive one for the parent's judgement is a real and easy saving (Chapter 27).

Note that the parent does **not** get the subagent's tools:

```
parent tools: ['ls', 'read_file', 'write_file', 'edit_file', 'delete', 'glob', 'grep', 'task']
```

Delegation is how the parent reaches them — which is also a way to keep a dangerous tool out
of the main loop.

## When to delegate

**The subtask produces a lot of context and a small answer.** Reading five log files to
report one line. This is the archetype, and if it describes your subtask, delegate.

**The subtask needs different instructions.** A critic that must not be encouraging; a
formatter with a rigid house style.

**The subtask needs different tools.** Or a different model.

**The subtasks are independent.** Several `task` calls can run concurrently.

## When not to

**The answer is the context.** If the parent needs everything the subagent read, isolation
costs you a round trip and buys nothing.

**The subtask is one tool call.** Just call the tool.

**The subtask needs to negotiate.** There is no conversation. One brief, one answer.

**You are building a hierarchy for its own sake.** Deep trees of agents are the most
over-applied pattern in this ecosystem: every level is a model call, context is lost at every
boundary, and debugging spans several transcripts. One level of delegation is usually right;
three is usually a design that has got away from you.

## Returning more than a sentence

The `task` result is a string, which is the main constraint. When the subagent has more to
say, have it **write a file** (Chapter 7):

```
system_prompt: "Write your full analysis to /analysis/<topic>.md, then reply with
                one line saying what you found and the path you wrote."
```

Now the parent gets a summary *and* a pointer, and can read the file if it needs detail. The
filesystem is shared; the context is not. That combination is the most useful thing in this
chapter.

## Cost

Delegation is not free. Each subagent call is at least one model call with its own system
prompt and the harness's ~2,400 tokens of tool definitions. A subagent that saves 500 tokens
of context costs more than it saves.

Delegate when the context saved is **large** — a log file, a document, a directory listing —
not to be tidy.

## Debugging

Subagent work is invisible in the parent's transcript, which is the feature and the debugging
problem. A subagent that fails silently returns a plausible sentence and the parent proceeds.

Three habits:

- **Have subagents write files.** Then their work is inspectable afterwards.
- **Stream with `subgraphs=True`** to see inside (Chapter 22).
- **Suspect the `description`** when the answer is wrong. It is usually an underspecified
  brief rather than a bad subagent.

## Try it

Prove the isolation:

```bash
uv run python -c "
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from examples.scout.fakes import ScriptedModel

seen = []
class Spy(ScriptedModel):
    def _generate(self, messages, *a, **k):
        seen.append(len(messages))
        return super()._generate(messages, *a, **k)

sub = {'name':'log-reader','description':'Reads a log.','system_prompt':'Report one line.'}
m = Spy(script=[
    {'text':'delegating','tool_calls':[{'name':'task','args':{'description':'summarise /logs/api.log','subagent_type':'log-reader'}}]},
    {'text':'sub: disk full at 09:41'},
    'parent: root cause is disk'])
out = create_deep_agent(model=m, subagents=[sub]).invoke(
    {'messages':[{'role':'user','content':'investigate'}],
     'files':{'/logs/api.log': create_file_data('ERROR disk full')}})
print('messages per model call:', seen)
for x in out['messages']:
    print(f'  {type(x).__name__:13} {str(x.content)[:50]!r}')
"
```

The middle number is the subagent starting fresh. The parent's transcript contains its
conclusion and nothing else.

## Takeaways

- `task(description, subagent_type)` runs a fresh agent and returns **only its answer**.
- Measured, the subagent's model call saw **2 messages, not the parent's history** — and none
  of its reading reached the parent's context.
- **A subagent spends context you do not pay for afterwards.** That is the entire point.
- **The `description` is the whole brief.** There is no follow-up, and a vague brief produces
  a vague answer the parent cannot detect.
- Subagents can have their own tools and model; the parent does not inherit them, which is
  also a way to keep a dangerous tool out of the main loop.
- Delegate when the subtask produces **a lot of context and a small answer**. Not when the
  answer *is* the context, not for one tool call, and not to build a hierarchy.
- **Have subagents write files** and reply with a path. Shared filesystem, isolated context.
- Each delegation costs a model call plus ~2,400 tokens of tool definitions — delegate for
  large savings, not tidiness.
- Their work is invisible in the parent transcript. Write files, stream with `subgraphs=True`,
  and suspect the brief first.

---

Previous: [Chapter 8 — Backends](08-backends.md) ·
Next: [Chapter 10 — Skills](10-skills.md)
