"""Deterministic stand-ins for a chat model and an embedding model.

Every example in this book runs offline, for free, and prints the same thing
every time. That is only possible because these two classes replace the parts
that would otherwise cost money and vary between runs.

Both are honest about what they are. `ScriptedModel` replays fixed replies with
real tool calls, so `create_agent` drives it exactly as it drives a real model.
`LexicalEmbeddings` scores on *vocabulary overlap* rather than meaning -- enough
to demonstrate how retrieval works, and Chapter 15 is explicit about the
difference, because that difference is itself worth teaching.
"""

from __future__ import annotations

import math
import re
import zlib
from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

# --- the chat model ---------------------------------------------------------


class ScriptedModel(BaseChatModel):
    """Replays `script` one entry per call, then repeats the last entry.

    Each entry is a string, or a dict with `text` and/or `tool_calls`, where a
    tool call is `{"name": ..., "args": {...}}`.
    """

    script: list[Any]
    cursor: list[int] = [0]
    bound_tools: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    @property
    def calls(self) -> int:
        return self.cursor[0]

    def _next(self) -> AIMessage:
        idx = min(self.cursor[0], len(self.script) - 1)
        self.cursor[0] += 1
        entry = self.script[idx]
        if isinstance(entry, str):
            entry = {"text": entry}
        tool_calls = [
            {"name": tc["name"], "args": tc.get("args", {}), "id": f"call_{idx}_{i}"}
            for i, tc in enumerate(entry.get("tool_calls", []))
        ]
        return AIMessage(
            content=entry.get("text", ""),
            tool_calls=tool_calls,
            # Fixed counts keep Chapter 28's cost arithmetic reproducible.
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next())])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """One chunk per word, so Chapter 22's streaming output is observable."""
        msg = self._next()
        words = str(msg.content).split(" ")
        for i, word in enumerate(words):
            text = word if i == len(words) - 1 else word + " "
            yield ChatGenerationChunk(message=AIMessageChunk(content=text))
        if msg.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", tool_calls=msg.tool_calls)
            )

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ScriptedModel":
        """Record the names and return *self*, deliberately.

        `create_agent` re-binds tools on every step. Returning a copy would give
        that copy a fresh `cursor` (this is a pydantic model), restarting the
        script each step -- an infinite loop if entry 0 calls a tool.
        """
        self.bound_tools = [
            getattr(t, "name", getattr(t, "__name__", str(t))) for t in tools
        ]
        return self


# --- the embedding model ----------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+")

# Words too common to carry meaning. A real embedding model has no equivalent;
# it learns this from data. Ours needs telling.
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "who", "why", "with", "you", "your", "do",
    "does", "can", "if", "my", "we", "our",
}


class LexicalEmbeddings(Embeddings):
    """A toy embedding: one dimension per vocabulary word, weighted by count.

    Cosine similarity between two of these vectors is real word overlap, so
    retrieval in this book genuinely works and its results are explainable --
    you can read the documents and predict the ranking.

    What it is NOT is semantic. "refund" and "reimbursement" are unrelated here
    and close together in a real embedding model. Chapter 15 measures that gap
    rather than glossing over it.
    """

    def __init__(self, dims: int = 512) -> None:
        self.dims = dims

    def _vector(self, text: str) -> list[float]:
        counts: dict[int, float] = {}
        for word in _WORD.findall(text.lower()):
            if word in _STOP or len(word) < 2:
                continue
            # Stem crudely, so "refunds" and "refund" share a dimension.
            word = re.sub(r"(ies|es|s)$", "", word)
            # NOT hash(): Python randomises string hashing per process, so the
            # "deterministic" embedding would differ between runs and every
            # retrieval output printed in this book would be wrong tomorrow.
            slot = zlib.crc32(word.encode()) % self.dims
            counts[slot] = counts.get(slot, 0.0) + 1.0
        vec = [0.0] * self.dims
        for slot, count in counts.items():
            vec[slot] = 1.0 + math.log(count)

        if not counts:
            # Every word was a stop word, too short, or the text was empty. An
            # all-zero vector has no direction, and cosine similarity against it
            # is 0/0 -- which surfaces as "NaN values found" from the vector
            # store rather than as anything mentioning this function. Park such
            # texts on one reserved dimension instead: a valid unit vector that
            # matches other contentless text and nothing else.
            vec[0] = 1.0
            return vec

        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
