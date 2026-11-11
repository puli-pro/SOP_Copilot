"""LLM provider. Ollama only for now; the interface is one function so a hosted API can be added."""
import json

import httpx

from app import config


class LLMUnavailable(Exception):
    """Ollama is not running, or the model has not been pulled yet."""


def health() -> dict:
    try:
        r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        base = config.OLLAMA_MODEL.split(":")[0]
        ready = any(n == config.OLLAMA_MODEL or n.split(":")[0] == base and ":" not in config.OLLAMA_MODEL for n in names)
        return {"reachable": True, "model": config.OLLAMA_MODEL, "model_ready": ready, "installed": names}
    except Exception as e:  # noqa: BLE001
        return {"reachable": False, "model": config.OLLAMA_MODEL, "model_ready": False, "error": str(e)}


def generate_json(system: str, user: str) -> dict:
    """Ask the model for a JSON object. Raises LLMUnavailable if it cannot be reached."""
    payload = {
        "model": config.OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 4096},
        "keep_alive": "2h",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    try:
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=config.OLLAMA_TIMEOUT)
    except httpx.HTTPError as e:
        raise LLMUnavailable(f"Could not reach Ollama at {config.OLLAMA_URL}: {e}") from e
    if r.status_code == 404:
        raise LLMUnavailable(f"Model '{config.OLLAMA_MODEL}' is not installed. Run: ollama pull {config.OLLAMA_MODEL}")
    if r.status_code != 200:
        raise LLMUnavailable(f"Ollama returned HTTP {r.status_code}: {r.text[:200]}")
    content = r.json().get("message", {}).get("content", "")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"answerable": False, "answer": "", "citations": [], "_parse_error": content[:200]}
