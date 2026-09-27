"""Chat/generation backends: real Foundry Local, or an offline fallback.

Same pattern as embeddings.py: prefer a real local model served by Foundry
Local, fall back to a small extractive responder that needs no model
download at all.
"""

from . import config


class LLMBackend:
    """Common interface: a `name` attribute and an `answer(...)` method."""

    name: str

    def answer(self, question: str, context_chunks: list[dict]) -> str:
        raise NotImplementedError


def _build_prompt(question: str, context_chunks: list[dict]) -> str:
    context_block = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
    )
    return (
        f"Context passages:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer using only the context above."
    )


class FoundryLocalLLM(LLMBackend):
    name = "foundry-local"

    def __init__(self, alias: str = config.LLM_MODEL_ALIAS):
        from .foundry_runtime import get_ready_model

        model = get_ready_model(alias)
        self._client = model.get_chat_client()
        # Fail fast if inference doesn't actually work.
        self._client.complete_chat([{"role": "user", "content": "ping"}])

    def answer(self, question: str, context_chunks: list[dict]) -> str:
        if not context_chunks:
            return "I don't know - no relevant documents were found in the knowledge base."
        messages = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(question, context_chunks)},
        ]
        response = self._client.complete_chat(messages)
        return response.choices[0].message.content.strip()


class ExtractiveFallbackLLM(LLMBackend):
    """No generative model available: return the most relevant passages directly.

    This keeps the pipeline fully functional and honest (it never invents an
    answer) when Foundry Local isn't installed on the grading machine.
    """

    name = "offline-extractive-fallback"

    def answer(self, question: str, context_chunks: list[dict]) -> str:
        if not context_chunks:
            return (
                "I don't know - no relevant documents were found in the knowledge base. "
                "(Running in offline fallback mode: install Foundry Local for generative answers.)"
            )
        lines = [
            "[Offline fallback mode - showing the most relevant passages verbatim; "
            "install Foundry Local for a generated answer.]",
            "",
        ]
        for c in context_chunks:
            snippet = c["text"].strip().replace("\n", " ")
            if len(snippet) > 400:
                snippet = snippet[:400].rsplit(" ", 1)[0] + "..."
            lines.append(f"- ({c['source']}) {snippet}")
        return "\n".join(lines)


def get_llm_backend() -> LLMBackend:
    try:
        backend = FoundryLocalLLM()
        print(f"[llm] Using Foundry Local model '{config.LLM_MODEL_ALIAS}'.")
        return backend
    except Exception as exc:  # noqa: BLE001 - any failure means "not available"
        print(
            f"[llm] Foundry Local not available ({exc.__class__.__name__}: {exc}). "
            "Falling back to offline extractive responder."
        )
        return ExtractiveFallbackLLM()
