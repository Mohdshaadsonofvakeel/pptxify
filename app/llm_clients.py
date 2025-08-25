# app/llm_clients.py
"""
Provider-agnostic LLM call wrappers.
We support: OpenAI, Anthropic, Gemini, and OpenAI-compatible base_url.
We never persist or log API keys. All requests are made in-memory.
"""
import json
import os
from typing import Dict, Any, Optional
import requests


OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _outline_prompt(text: str, guidance: str, include_notes: bool) -> Dict[str, Any]:
    system = (
        "You are a presentation planning assistant. "
        "Given raw text or markdown and a short guidance string, produce a slide outline.\n"
        "Return STRICT JSON with this schema:\n"
        "{\n"
        "  \"title\": string,\n"
        "  \"slides\": [\n"
        "     {\"title\": string, \"bullets\": [string, ...], "
        + ("\"notes\": string, " if include_notes else "")
        + "\"layout\": string}\n"
        "  ],\n"
        "  \"estimated_slide_count\": number\n"
        "}\n"
        "Pick a reasonable number of slides (8–25 typical). Use concise bullets (max ~14 words). "
        "Prefer 'Title and Content' layout unless an image would help, then 'Content with Caption' or 'Two Content'. "
        "If no layout hint, set layout to \"auto\"."
    )
    user = (
        f"GUIDANCE: {guidance or 'none'}\n"
        "INPUT TEXT:\n"
        f"{text}\n\n"
        "Output ONLY valid JSON object, no markdown fences."
    )
    return {"system": system, "user": user}


def plan_slides_via_llm(
    text: str,
    guidance: str,
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    include_notes: bool = False,
) -> Dict[str, Any]:
    prompt = _outline_prompt(text, guidance, include_notes)
    provider = (provider or "").strip().lower()

    if provider in ("openai", "oai"):
        return _openai_chat_json(prompt, api_key, model or OPENAI_DEFAULT_MODEL, base_url)
    elif provider in ("anthropic", "claude"):
        return _anthropic_messages_json(prompt, api_key, model or ANTHROPIC_DEFAULT_MODEL)
    elif provider in ("gemini", "google", "vertex"):
        return _gemini_generate_json(prompt, api_key, model or GEMINI_DEFAULT_MODEL)
    elif provider in ("openai-compatible", "oai-compatible", "compatible"):
        if not base_url:
            raise ValueError("base_url required for openai-compatible provider")
        return _openai_chat_json(prompt, api_key, model or OPENAI_DEFAULT_MODEL, base_url=base_url.rstrip("/"))
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ---------------- OpenAI (and OpenAI-compatible) ----------------
def _openai_chat_json(prompt: Dict[str, str], api_key: str, model: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    # Use Chat Completions with JSON mode for widest compatibility
    url = (base_url or "https://api.openai.com").rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenAI error: {resp.status_code} {resp.text}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


# ---------------- Anthropic ----------------
def _anthropic_messages_json(prompt: Dict[str, str], api_key: str, model: str) -> Dict[str, Any]:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 2000,
        "temperature": 0.2,
        "system": prompt["system"],
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt["user"]}]}],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Anthropic error: {resp.status_code} {resp.text}")
    data = resp.json()
    # Messages API returns a list of content blocks; we expect a single text block
    text = ""
    if "content" in data and data["content"]:
        for block in data["content"]:
            if block.get("type") == "text":
                text += block.get("text", "")
    if not text:
        raise RuntimeError("Anthropic returned no text content")
    return json.loads(text)


# ---------------- Gemini ----------------
def _gemini_generate_json(prompt: Dict[str, str], api_key: str, model: str) -> Dict[str, Any]:
    # Gemini REST API (generateContent)
    base = "https://generativelanguage.googleapis.com"
    path = f"/v1beta/models/{model}:generateContent"
    url = f"{base}{path}?key={api_key}"
    headers = {"content-type": "application/json"}
    contents = [
        {
            "role": "user",
            "parts": [{"text": f"{prompt['system']}\n\n{prompt['user']}"}],
        }
    ]
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2000},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini error: {resp.status_code} {resp.text}")
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"Gemini unexpected response: {data}")
    return json.loads(text)
