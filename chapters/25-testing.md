# Chapter 25 — Testing

A deep agent is long, non-deterministic and file-producing, which sounds untestable and is
not. The model's judgement is non-deterministic; your configuration, tools, prompts and the
harness's behaviour are not.

## Four layers

| Layer | What | Needs a model? |
|---|---|---|
| 1 | **Configuration** — is the capability enabled? | no |
| 2 | Tools, prompts, workspace | no |
| 3 | Harness behaviour, with a scripted model | scripted |
| 4 | The expensive failure modes | scripted |

The book's suite:

```
19 passed in 3.13s
```

No API key, no network.

## Layer 1 is specific to this library

Elsewhere you test behaviour. Here you first test that the thing exists, because absence is
silent (Chapter 19):

```python
def _offered(**kwargs) -> list[str]:
    model = ScriptedModel(script=["ok"])
    create_deep_agent(model=model, **kwargs).invoke({"messages": [{"role": "user", "content": "hi"}]})
    return model.bound_tools

def test_planning_is_opt_in():
    assert "write_todos" not in _offered()
    assert "write_todos" in _offered(middleware=[TodoListMiddleware()])

def test_the_example_enables_planning():
    model = ScriptedModel(script=["ok"])
    build(model=model).invoke({"messages": [{"role": "user", "content": "hi"}]})
    assert "write_todos" in model.bound_tools
```

The first documents the library's behaviour and will fail loudly if a future version changes
it. The second asserts *your* agent enabled it — the bug that actually bites.

Do the same for tool descriptions, which vanish without `parse_docstring=True`:

```python
def test_custom_tools_expose_argument_descriptions():
    for tool in TOOLS:
        for name, schema in tool.args.items():
            assert "description" in schema, f"{tool.name}.{name} has no description"
```

## Test the prompt's load-bearing lines

Chapter 12 identified lines that carry real weight. Assert they survive:

```python
def test_system_prompt_names_the_output_path():
    assert "/findings.md" in SYSTEM_PROMPT

def test_system_prompt_permits_failure():
    assert "does not support" in SYSTEM_PROMPT
```

Crude, and it means nobody deletes them during a tidy-up without a red build. Assert
*properties*, never wording.

## Layer 3: behaviour, scripted

With a fixed script the harness is deterministic, so you can assert on what it *did*:

```python
def test_investigation_writes_a_report():
    out = investigate()
    assert "/findings.md" in out["files"]

def test_investigation_cites_its_sources():
    report = investigate()["files"]["/findings.md"]["content"]
    assert "[/logs/api.log]" in report
    assert "[/runbooks/disk.md]" in report

def test_investigation_keeps_a_plan():
    assert len(investigate().get("todos", [])) == 3
```

**Assert on files and todos, not on prose.** The report's wording will change; the fact that
it exists and carries citations should not.

And the check Chapter 18 argued for — that the run did not succeed *over* a broken filesystem:

```python
def test_no_tool_errored():
    errors = [str(m.content) for m in investigate()["messages"]
              if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)]
    assert not errors, errors
```

That one test catches path changes, a renamed seed file, and a backend misconfiguration.

## Layer 4: the failures that cost money

Free to test, expensive to hit:

```python
def test_runaway_hits_the_recursion_limit():
    forever = [{"text": "again", "tool_calls": [{"name": "ls", "args": {"path": "/"}}]}]
    with pytest.raises(GraphRecursionError):
        create_deep_agent(model=ScriptedModel(script=forever)).invoke(payload, {"recursion_limit": 8})

def test_call_limit_stops_gracefully():
    out = create_deep_agent(model=ScriptedModel(script=forever),
                            middleware=[ModelCallLimitMiddleware(run_limit=4)]).invoke(payload, ...)
    assert out["messages"]     # completed, not raised
```

## Test the traps as documentation

Some tests exist to record behaviour you must not forget:

```python
def test_files_do_not_persist_without_a_checkpointer():
    first = agent.invoke(payload)
    second = agent.invoke(payload)
    assert "/a.md" in first["files"]
    assert second["files"] == {}
```

Asserting a *limitation* is unusual and useful: it is executable documentation, and it tells
you loudly if a future version changes the behaviour your code relies on.

## A lesson from writing these

One test failed for a reason worth passing on. `test_threads_are_isolated` used a script long
enough for one run and invoked twice. The second thread wrote nothing — and it looked like a
threading bug.

It was the fake: **a `ScriptedModel` shares one cursor across runs**, so the second invocation
got only the repeated last entry. The library was fine.

The general point: **when a test involving a fake fails, suspect the fake first.** The
comment in the test now says so.

## Testing subagents

Isolation is assertable (Chapter 9):

```python
def test_subagent_context_is_isolated():
    seen = []
    class Spy(ScriptedModel):
        def _generate(self, messages, *a, **k):
            seen.append(len(messages))
            return super()._generate(messages, *a, **k)
    ...
    assert seen[1] <= seen[0], f"subagent inherited context: {seen}"
```

Counting messages per model call is the cleanest way to prove a property that is otherwise
invisible.

## What this does not test

Whether the conclusion is *right*. That is evaluation — a dataset of incidents with known root
causes, scored — and it costs money, is slow, and produces a score rather than pass/fail.
Chapter 26 covers it. Keep it out of the unit suite, or the unit suite stops being run.

## Try it

```bash
uv run --extra dev pytest -q
```

```
19 passed in 3.13s
```

Then break things and watch which test catches each. Remove `TodoListMiddleware` from `build`
in [`examples/scout/agent.py`](../examples/scout/agent.py) — `test_the_example_enables_planning`
fails. Delete `/findings.md` from `SYSTEM_PROMPT` — the prompt test fails. Change a seeded
path in `workspace.py` — `test_no_tool_errored` fails.

## Takeaways

- The model is non-deterministic; **configuration, tools, prompts and harness behaviour are
  not**. 19 tests, 3 seconds, no API key.
- **Layer 1 is specific to this library: test that capabilities are enabled**, because absence
  is silent. `bound_tools` is the check.
- Assert the prompt's **load-bearing lines** exist — output path, permission to fail — so a
  tidy-up cannot delete them quietly.
- **Assert on files and todos, not prose.** Wording changes; the deliverable's existence and
  citations should not.
- **`test_no_tool_errored`** catches a run that succeeded over a broken filesystem — one of
  the highest-value tests here.
- Test the money failures: runaway loops and graceful caps, both free.
- **Assert known limitations too** — executable documentation that reports when the library
  changes.
- **When a test involving a fake fails, suspect the fake first.**
- Evaluation of whether the answer is *right* is separate, paid, and does not belong in CI.

---

Previous: [Chapter 24 — Structuring a real project](24-project-structure.md) ·
Next: [Chapter 26 — Evaluating a deep agent](26-evaluation.md)
