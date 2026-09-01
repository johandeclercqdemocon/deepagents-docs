# Chapter 26 — Evaluating a deep agent

Chapter 25 tested mechanics. This chapter is the harder question: was the agent any *good*?

For a chain, evaluation is mostly "is the answer right". For a deep agent it is not, because
the answer is the smallest part of what it produced.

## Four things worth scoring

| What | Question | Cost to score |
|---|---|---|
| **Outcome** | did it reach the right conclusion? | needs labels |
| **Artefacts** | is the file it wrote any good? | needs a judge or a human |
| **Process** | did it work sensibly to get there? | **free** |
| **Efficiency** | how many turns and tokens? | **free** |

Two of those are free and deterministic, and almost nobody scores them. Start there.

## Process metrics you already have

Everything needed is in the result:

```python
out = investigate()

turns   = sum(1 for m in out["messages"] if type(m).__name__ == "AIMessage")
tools   = [m for m in out["messages"] if type(m).__name__ == "ToolMessage"]
errors  = [m for m in tools if "Error" in str(m.content)]
files   = sorted(out["files"])
todos   = out.get("todos", [])
done    = sum(1 for t in todos if t["status"] == "completed")
```

Scored across a set of incidents, these answer questions an outcome score cannot:

- **Did it produce the artefact at all?** A run with no `/findings.md` failed regardless of
  what the final message says. This is the single most useful check.
- **Did it finish its plan?** Todos still `pending` at the end means it gave up quietly.
- **Did tools error?** A rising rate means the environment drifted, not the model.
- **Did it get more expensive?** Turns per run is a regression signal that catches prompt
  changes making the agent wander.

None needs a label or a judge. Run them over ten recorded incidents and you have a baseline
that will catch most regressions.

## Outcome scoring

For `scout`, the label is the known root cause:

```python
CASES = [
    ("node-3 disk", "/logs/api.log has 'no space left on device'", "disk"),
    ("node-7 registration", "403 on REGISTER", "realm mismatch"),
]
```

Score by keyword, by structured field (Chapter 15 — `root_cause` as a `Literal` makes this
exact), or by a judge. **Prefer the structured field**: it turns a fuzzy comparison into an
equality check, and it is free.

This is the strongest practical argument for `response_format` on an agent you intend to
evaluate.

## Scoring the artefact

The file is the deliverable, so it needs judging. `RubricMiddleware` grades against criteria
you write:

```python
from deepagents.middleware import RubricMiddleware

RubricMiddleware(model=grader_model, ...)
```

Check the signature on your installed version — it takes a `model` and criteria, and it costs
a model call per grading.

Rubric criteria that work for a report:

- Does every claim carry a source?
- Are the required sections present? (Chapter 10's skill defines them.)
- Does it state what it could not determine?
- Is the stated root cause supported by the cited evidence?

Note the first three are **checkable without a model**. Citation presence is a regex. Section
headings are a string match. Only the last needs judgement — so score the cheap ones
deterministically and reserve the judge for the one that needs it.

That split is the practical lesson: **most rubric criteria are assertions in disguise.**

## Judges, carefully

Where a judge is genuinely needed:

- **Give it the rubric and the evidence**, not just the report.
- **Calibrate against human labels** on a sample. An uncalibrated judge is a number, not a
  measurement.
- Judges favour longer, more confident writing — which is exactly the failure mode you are
  trying to detect in an agent that fabricates.
- Use scores to **compare versions**, never as absolute claims.

## Building the dataset

The best source is production. When a run goes wrong, that incident goes in the set — with its
seeded workspace, so it is reproducible.

Ten real incidents beat a hundred invented ones, because invented incidents have tidy logs and
real ones do not.

Store the whole input: the question **and** the `files` seed. A deep agent's behaviour depends
on its workspace, so a case without one is not reproducible.

## Keep it out of CI

Evaluation is slow, costs money, and produces a score. Run it before releases and after prompt
changes.

The exception, as with the other books: **the free process metrics belong in CI.** "Produced a
file", "no tool errors", "finished the plan", "under N turns" are deterministic assertions,
and they catch a surprising share of regressions.

## Try it

Compute process metrics on a run — no labels, no judge:

```bash
uv run python -c "
from examples.scout.agent import investigate
out = investigate()
tools = [m for m in out['messages'] if type(m).__name__ == 'ToolMessage']
todos = out.get('todos', [])
print('turns      :', sum(1 for m in out['messages'] if type(m).__name__ == 'AIMessage'))
print('tool calls :', len(tools))
print('tool errors:', sum(1 for m in tools if 'Error' in str(m.content)))
print('produced   :', [f for f in out['files'] if f == '/findings.md'] or 'NOTHING')
print('plan done  :', sum(1 for t in todos if t['status'] == 'completed'), '/', len(todos))
"
```

Then the cheap artefact checks, which need no judge:

```bash
uv run python -c "
import re
from examples.scout.agent import investigate
report = investigate()['files']['/findings.md']['content']
claims = [l for l in report.splitlines() if l.strip().startswith('-')]
cited  = [l for l in claims if re.search(r'\[[^\]]+\]', l)]
print(f'claims: {len(claims)}, cited: {len(cited)}')
print('every claim cited:', len(claims) == len(cited))
"
```

## Takeaways

- Four things to score: **outcome**, **artefact**, **process**, **efficiency**. The last two
  are free and deterministic — start there.
- The most useful single check is **did it produce the artefact at all**. A run with no file
  failed, whatever the final message claims.
- Unfinished todos mean it gave up quietly; rising tool errors mean the environment drifted;
  rising turns mean a prompt change made it wander.
- For outcome scoring, **a structured `response_format` field turns fuzzy comparison into
  equality** — the strongest argument for using one.
- `RubricMiddleware` grades artefacts, at a model call each. But **most rubric criteria are
  assertions in disguise** — citations, sections, stated unknowns are all checkable for free.
  Reserve the judge for judgement.
- Calibrate judges against humans; they favour long, confident writing, which is the failure
  you are hunting.
- Build the dataset from **real failed runs, with their workspace**, or the case is not
  reproducible.
- Keep evaluation out of CI — **except the free process metrics**, which belong there.

---

Previous: [Chapter 25 — Testing](25-testing.md) ·
Next: [Chapter 27 — Cost and context](27-cost.md)
