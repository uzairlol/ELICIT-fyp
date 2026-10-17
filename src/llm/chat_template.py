"""Fixed chat-template rendering for cross-model prompt parity.

Each model family ships its own default chat template: ChatML for Qwen, a
Llama-3 header with `` for Llama, ``[INST]...[/INST]`` for Mistral. If the
serving stack applies the served model's template, then the *same* P0 prompt is
a different token sequence per family — which silently reintroduces exactly the
prompt confound the P1/P2 perturbations exist to measure, and makes
``sigma^2_model`` uninterpretable as a model effect.

Setting ``CHAT_TEMPLATE_MODE = "fixed"`` renders the chat string once, in Python,
and posts raw text to ``/v1/completions``. The prompt is then byte-identical
across families and the model factor is a model factor.

The legacy ``"server"`` mode is retained and remains the default, because it
changes the transport and must not change behaviour silently. Every grid config
that crosses model families must set ``"fixed"``.
"""

from __future__ import annotations

from typing import Any

from core import parameters


def _tok(name: str) -> str:
    """Build one model control token.

    Assembled from parts so the literal control sequence never appears in source,
    which keeps the tokens intact through editors, formatters and copy-paste.
    """
    return "<|" + name + "|>"


#: Supported templates. ``chatml`` is chosen because the canonical historical
#: arm ran Qwen2.5, whose default template is ChatML; using it everywhere makes
#: the fixed mode a strict superset of the server mode for the reference cell.
TEMPLATES: dict[str, dict[str, Any]] = {
    "chatml": {
        "bos": _tok("im_start"),
        "eos": _tok("im_end"),
        "generation_prompt": _tok("im_start") + "assistant\n",
    },
    "llama3": {
        "bos": _tok("begin_of_text"),
        "eos": _tok("eot_id"),
        "generation_prompt": "",
        "header": (
            _tok("start_header_id") + "user" + _tok("end_header_id") + "\n\n",
            _tok("eot_id") + _tok("start_header_id") + "assistant" + _tok("end_header_id") + "\n\n",
        ),
    },
    "mistral": {
        "bos": "",
        "eos": "",
        "generation_prompt": "",
    },
}

TEMPLATE_NAMES: tuple[str, ...] = tuple(TEMPLATES)

SYSTEM_PREFIX = "system\n"
USER_PREFIX = "user\n"
ASSISTANT_PREFIX = "assistant\n"


class UnknownTemplate(ValueError):
    """Raised when a config names a chat template that is not registered."""


def resolve_template(name: str | None = None) -> dict[str, Any]:
    """Return the template spec, defaulting to ``CHAT_TEMPLATE_NAME``."""
    resolved = str(name or getattr(parameters, "CHAT_TEMPLATE_NAME", "chatml"))
    try:
        return TEMPLATES[resolved]
    except KeyError:
        raise UnknownTemplate(
            f"Unknown chat template {resolved!r}. Known: {', '.join(TEMPLATE_NAMES)}"
        ) from None


def fixed_template_mode() -> bool:
    return str(getattr(parameters, "CHAT_TEMPLATE_MODE", "server")).lower() == "fixed"


def render_chat(text: str, template_name: str | None = None) -> str:
    """Render a single-user-turn prompt into one fully-templated string.

    The same function renders every decision stage, every agent and every model,
    so the resulting prompt is identical across model families by construction.
    """
    spec = resolve_template(template_name)
    name = str(template_name or getattr(parameters, "CHAT_TEMPLATE_NAME", "chatml"))

    if name == "chatml":
        return f"{spec['bos']}{USER_PREFIX}{text}{spec['eos']}{spec['generation_prompt']}"

    if name == "llama3":
        user_header, assistant_header = spec["header"]
        return f"{spec['bos']}{user_header}{text}{spec['eos']}{assistant_header}"

    # Mistral: [INST] ... [/INST]
    return f"[INST] {text} [/INST]"


def render_messages(messages: list[dict[str, str]], template_name: str | None = None) -> str:
    """Render a multi-turn message list. ELICIT only uses a single user turn."""
    spec = resolve_template(template_name)
    name = str(template_name or getattr(parameters, "CHAT_TEMPLATE_NAME", "chatml"))
    parts: list[str] = []
    if name == "mistral":
        for message in messages:
            if message.get("role") == "user":
                parts.append(f"[INST] {message.get('content', '')} [/INST]")
            else:
                parts.append(message.get("content", ""))
        return "".join(parts)
    for message in messages:
        role = str(message.get("role", "user"))
        parts.append(f"{spec['bos']}{role}\n{message.get('content', '')}{spec['eos']}")
    parts.append(spec["generation_prompt"])
    return "".join(parts)


def template_fingerprint(template_name: str | None = None) -> str:
    """Stable description of the rendered template, for the manifest."""
    import hashlib
    import json

    spec = resolve_template(template_name)
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
