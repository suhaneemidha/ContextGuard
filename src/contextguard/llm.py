"""Optional Groq-backed language model integration."""

import os

from dotenv import load_dotenv
from groq import Groq


DEFAULT_MODEL = "openai/gpt-oss-20b"


def generate_review_response(
    prompt: str,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Generate a JSON review response using Groq chat completions."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Review prompt must not be empty")

    load_dotenv()

    resolved_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
    if not resolved_key:
        raise ValueError(
            "Groq API key is missing. Set GROQ_API_KEY in your .env file."
        )

    resolved_model = (
        model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    ).strip()
    if not resolved_model:
        raise ValueError("Groq model name must not be empty")

    try:
        client = Groq(api_key=resolved_key)
        response = client.chat.completions.create(
            model=resolved_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a conservative code-review verification "
                        "assistant. Return only a valid JSON object matching "
                        "the response schema provided in the user prompt. "
                        "Never invent source evidence."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=2048,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq review request failed: {exc}") from exc

    if not response.choices:
        raise RuntimeError("Groq returned no completion choices")

    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Groq returned an empty review response")

    return content
