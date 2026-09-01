"""The test strategy from Chapter 25, applied to the book's running example.

    uv run --extra dev pytest -q

Four layers, cheapest first. No API key, no network.
"""

from __future__ import annotations

import pytest
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware
from langgraph.checkpoint.memory import InMemorySaver

from examples.scout.agent import SYSTEM_PROMPT, TOOLS, build, check_metric, investigate
from examples.scout.fakes import ScriptedModel
from examples.scout.workspace import FILES, seed

# --- Layer 1: configuration. Is the capability even there? -----------------


def _offered(**kwargs) -> list[str]:
    model = ScriptedModel(script=["ok"])
    create_deep_agent(model=model, **kwargs).invoke(
        {"messages": [{"role": "user", "content": "hi"}]}
    )
    return model.bound_tools


def test_harness_injects_its_tools() -> None:
    assert {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "task"} <= set(_offered())


def test_planning_is_opt_in() -> None:
    """Chapter 6: write_todos is NOT default. Guard against a silent regression."""
    assert "write_todos" not in _offered()
    assert "write_todos" in _offered(middleware=[TodoListMiddleware()])


def test_the_example_enables_planning() -> None:
    model = ScriptedModel(script=["ok"])
    build(model=model).invoke({"messages": [{"role": "user", "content": "hi"}]})
    assert "write_todos" in model.bound_tools


def test_custom_tools_expose_argument_descriptions() -> None:
    """Chapter 14: a bare @tool drops these silently."""
    for tool in TOOLS:
        for name, schema in tool.args.items():
            assert "description" in schema, f"{tool.name}.{name} has no description"


def test_system_prompt_names_the_output_path() -> None:
    """Chapter 12: the highest-value line. Nobody may delete it quietly."""
    assert "/findings.md" in SYSTEM_PROMPT


def test_system_prompt_permits_failure() -> None:
    assert "does not support" in SYSTEM_PROMPT


# --- Layer 2: the deterministic pieces --------------------------------------


def test_workspace_seeds_every_file() -> None:
    assert set(seed()) == set(FILES)


def test_check_metric_names_valid_options_when_unknown() -> None:
    """Chapter 3: a tool result must let the model stop."""
    assert "unknown metric" in check_metric.invoke({"name": "nonsense"})


# --- Layer 3: the harness's behaviour, with a scripted model ---------------


def test_investigation_writes_a_report() -> None:
    out = investigate()
    assert "/findings.md" in out["files"]
    assert "disk" in out["files"]["/findings.md"]["content"].lower()


def test_investigation_cites_its_sources() -> None:
    """Chapter 12: every claim carries a source."""
    report = investigate()["files"]["/findings.md"]["content"]
    assert "[/logs/api.log]" in report
    assert "[/runbooks/disk.md]" in report


def test_investigation_keeps_a_plan() -> None:
    assert len(investigate().get("todos", [])) == 3


def test_seeded_files_survive_the_run() -> None:
    out = investigate()
    assert set(FILES) <= set(out["files"])


def test_no_tool_errored() -> None:
    """Chapter 18: the run can succeed while every tool call failed."""
    errors = [
        str(m.content)
        for m in investigate()["messages"]
        if type(m).__name__ == "ToolMessage" and "Error" in str(m.content)
    ]
    assert not errors, errors


# --- Layer 4: the failure modes that cost money ----------------------------


def test_runaway_hits_the_recursion_limit() -> None:
    """Chapter 21: guard the expensive failure, for free."""
    from langgraph.errors import GraphRecursionError

    forever = [{"text": "again", "tool_calls": [{"name": "ls", "args": {"path": "/"}}]}]
    with pytest.raises(GraphRecursionError):
        create_deep_agent(model=ScriptedModel(script=forever)).invoke(
            {"messages": [{"role": "user", "content": "go"}]}, {"recursion_limit": 8}
        )


def test_call_limit_stops_gracefully() -> None:
    """The same runaway, capped: completes with state intact instead of raising."""
    forever = [{"text": "again", "tool_calls": [{"name": "ls", "args": {"path": "/"}}]}]
    out = create_deep_agent(
        model=ScriptedModel(script=forever),
        middleware=[ModelCallLimitMiddleware(run_limit=4)],
    ).invoke({"messages": [{"role": "user", "content": "go"}]}, {"recursion_limit": 50})
    assert out["messages"]


# --- State and persistence --------------------------------------------------


def test_files_do_not_persist_without_a_checkpointer() -> None:
    """Chapter 4: documents the trap, so a fix elsewhere cannot hide it."""
    agent = create_deep_agent(
        model=ScriptedModel(
            script=[
                {"text": "x", "tool_calls": [{"name": "write_file", "args": {"file_path": "/a.md", "content": "1"}}]},
                "done",
            ]
        )
    )
    first = agent.invoke({"messages": [{"role": "user", "content": "go"}]})
    second = agent.invoke({"messages": [{"role": "user", "content": "go"}]})
    assert "/a.md" in first["files"]
    assert second["files"] == {}


def test_files_persist_with_a_checkpointer() -> None:
    agent = create_deep_agent(
        model=ScriptedModel(
            script=[
                {"text": "x", "tool_calls": [{"name": "write_file", "args": {"file_path": "/a.md", "content": "1"}}]},
                "done",
                "and again",
            ]
        ),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "t"}}
    agent.invoke({"messages": [{"role": "user", "content": "go"}]}, config)
    assert "/a.md" in agent.invoke({"messages": [{"role": "user", "content": "again"}]}, config)["files"]


def test_threads_are_isolated() -> None:
    """A second thread starts clean -- no files and no history from the first.

    Note the script is long enough for both runs: a ScriptedModel shares one
    cursor, so a script sized for one run leaves the second with only the
    repeated last entry and nothing to write. That is a property of the fake,
    not of threads, and it is worth stating because it looked like a bug.
    """
    write = {"text": "x", "tool_calls": [{"name": "write_file", "args": {"file_path": "/a.md", "content": "1"}}]}
    agent = create_deep_agent(
        model=ScriptedModel(script=[write, "done", write, "done"]),
        checkpointer=InMemorySaver(),
    )
    first = agent.invoke({"messages": [{"role": "user", "content": "go"}]}, {"configurable": {"thread_id": "a"}})
    second = agent.invoke({"messages": [{"role": "user", "content": "go"}]}, {"configurable": {"thread_id": "b"}})

    assert "/a.md" in first["files"]
    assert "/a.md" in second["files"]          # written again, on its own thread
    assert len(second["messages"]) == 4        # human, AI, tool, AI -- and none from thread a


# --- Subagents --------------------------------------------------------------


def test_subagent_context_is_isolated() -> None:
    """Chapter 9: the subagent must not inherit the parent's history."""
    seen: list[int] = []

    class Spy(ScriptedModel):
        def _generate(self, messages, *args, **kwargs):
            seen.append(len(messages))
            return super()._generate(messages, *args, **kwargs)

    sub = {"name": "reader", "description": "Reads a log.", "system_prompt": "One line."}
    model = Spy(
        script=[
            {"text": "delegating", "tool_calls": [{"name": "task", "args": {"description": "read it", "subagent_type": "reader"}}]},
            "sub answer",
            "parent answer",
        ]
    )
    create_deep_agent(model=model, subagents=[sub]).invoke(
        {"messages": [{"role": "user", "content": "go"}], "files": {"/l.log": create_file_data("ERROR")}}
    )
    # parent starts small, subagent starts small too, parent grows.
    assert seen[1] <= seen[0], f"subagent inherited context: {seen}"
