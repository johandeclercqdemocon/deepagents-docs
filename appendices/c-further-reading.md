# Appendix C — Further reading

## Official documentation

**[docs.langchain.com](https://docs.langchain.com)** — Deep Agents is at
`/oss/python/deepagents/overview`. The only source worth trusting by default, because it
tracks the current version.

**[docs.langchain.com/llms.txt](https://docs.langchain.com/llms.txt)** — an index of every page
with a description. Point an AI assistant here first; it is the difference between a current
answer and one describing an API that was removed.

**The repository** — [`langchain-ai/deepagents`](https://github.com/langchain-ai/deepagents).
Read release notes before upgrading; this is a pre-1.0 library moving faster than the two
beneath it. Several findings in this book came from reading the source and the docstrings —
`FilesystemBackend.__doc__` is where `virtual_mode`'s real meaning is documented, and it
contradicts the name.

**Read the docstrings.** More than in the other books, this library's docstrings are ahead of
its prose documentation:

```python
from deepagents.backends import FilesystemBackend
print(FilesystemBackend.__doc__)
```

## The other books in this set

Deep Agents sits on two layers, and its errors frequently belong to them.

**[LangChain: From First Call to Production](https://github.com/johandeclercqdemocon/langchain-docs)**
— models, tools, prompts, structured output, retrieval, `create_agent`. Read it if tool
schemas, `parse_docstring`, `response_format` or middleware are giving you trouble.

**[LangGraph: From First Graph to Production](https://github.com/johandeclercqdemocon/langgraph-docs)**
— state, checkpointers, threads, interrupts, the recursion limit. Read it when you see
`InvalidUpdateError`, `GraphRecursionError`, or anything about persistence — those are its
errors, not Deep Agents'. Chapter 31 explains when to write a graph instead of using the
harness.

## On the problems, not the library

**Anthropic, "Building effective agents"** — the best short argument for using the simplest
thing that works and against reaching for multi-agent architectures early. Chapter 30's
ordering agrees with it, and Chapter 1's "use `create_agent` until it breaks" is the same
argument.

**Simon Willison's writing on prompt injection** — the clearest explanation of why
prompt-level defences do not work. Chapter 28 extends it: a deep agent reads far more, and an
injection written to long-term memory persists across sessions.

**Anything serious on evaluation.** Chapter 26 is a starting point, not a treatment. The gap
between "it worked on my incident" and "it works on incidents I have not seen" is a
measurement problem.

## Adjacent tools

**LangSmith** — tracing and evaluation. Works unchanged, including subagents, with
`LANGSMITH_*` variables. → Ch 22

**Managed Deep Agents** — a hosted deployment path for this stack. Worth comparing against
Chapter 29's job-and-poll shape if you would rather not operate it yourself.

**Temporal** — durable execution done properly, nothing LLM-specific. If durability dominates
and the agentic part is small, compare seriously.

**OpenAI Agents SDK, Pydantic AI** — lighter agent frameworks with no harness. Worth knowing
so you can recognise when ~2,400 tokens of built-in tools is more than you need.

## How to read anything about Deep Agents

This library moves fastest of the five subjects in this set, and much written about it is
already wrong.

1. **Check your version.** `importlib.metadata.version("deepagents")`.
2. **Stop reading if it uses `backend=lambda rt: ...`** — factories were removed in 0.7.
3. **Do not believe "planning is enabled by default."** It is not, in 0.7.11. Check
   `bound_tools`.
4. **Prefer the docs and the docstrings** over blog posts.
5. **Run it.** Every claim in this book was checked by running it, and several were wrong
   until they were.

Findings measured while writing this book that contradict widely-published advice:

- **`write_todos` is not enabled by default**, despite the official skill description saying
  planning is built in.
- **Backend factories were removed in 0.7**, and the published examples still show them.
- **`StoreBackend(namespace=...)` takes a callable**, not a tuple.
- **`FilesystemBackend(virtual_mode=True)` still writes to real disk.**
- **`skills=[...]` without a backend silently does nothing.**

---

Previous: [Appendix B — Glossary](b-glossary.md) ·
Back to the [table of contents](../README.md)
