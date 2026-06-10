"""Chat-model factory — env-driven and provider-swappable.

Defaults to a **local LM Studio** server (OpenAI-compatible, free) so the
generator runs at zero cost during development. Set ``QUIZGEN_LLM_PROVIDER=anthropic``
to use Claude instead. The scoping graph never sees the difference.

Env vars:
  QUIZGEN_LLM_PROVIDER   "lmstudio" (default) | "anthropic"
  QUIZGEN_LLM_MODEL      model id — REQUIRED for lmstudio (the id loaded in LM
                         Studio, e.g. from `lms ps`); defaults to a Claude model
                         for anthropic
  QUIZGEN_LLM_BASE_URL   LM Studio base URL (default http://localhost:1234/v1)
  QUIZGEN_LLM_API_KEY    LM Studio key (any non-empty string; default "lm-studio")
  ANTHROPIC_API_KEY      required when provider=anthropic
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel, SecretStr


def _provider() -> str:
    return os.getenv("QUIZGEN_LLM_PROVIDER", "lmstudio").lower()


def get_chat_model(*, temperature: float = 0.7) -> BaseChatModel:
    """Build the configured chat model. LM Studio by default, Claude on request."""
    provider = _provider()
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("QUIZGEN_LLM_MODEL", "claude-sonnet-4-5"),
            temperature=temperature,
            timeout=None,
            stop=None,
        )
    if provider == "lmstudio":
        from langchain_openai import ChatOpenAI

        model = os.getenv("QUIZGEN_LLM_MODEL")
        if not model:
            raise ValueError(
                "QUIZGEN_LLM_MODEL is required for the lmstudio provider; set it to "
                "the model id loaded in LM Studio (see `lms ps`)."
            )
        return ChatOpenAI(
            base_url=os.getenv("QUIZGEN_LLM_BASE_URL", "http://localhost:1234/v1"),
            api_key=SecretStr(os.getenv("QUIZGEN_LLM_API_KEY", "lm-studio")),
            model=model,
            temperature=temperature,
        )
    raise ValueError(
        f"Unknown QUIZGEN_LLM_PROVIDER {provider!r}; use 'lmstudio' or 'anthropic'."
    )


def structured(
    schema: type[BaseModel], *, temperature: float = 0.7
) -> Runnable[Any, Any]:
    """Return a runnable that emits an instance of `schema` (a Pydantic model).

    Picks the structured-output method per provider: grammar-constrained
    ``json_schema`` for the OpenAI-compatible LM Studio server (reliable even on
    small local models), tool-based ``function_calling`` for Anthropic.
    """
    method = "function_calling" if _provider() == "anthropic" else "json_schema"
    return get_chat_model(temperature=temperature).with_structured_output(
        schema, method=method
    )
