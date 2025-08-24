# pptxify — Your Text, Your Style

Turn bulk text or markdown into a fully formatted PowerPoint **that matches the look & feel of your uploaded template**. Bring your own LLM API key (OpenAI, Anthropic, Gemini, or any OpenAI‑compatible endpoint). Keys are **never stored or logged**.

## Features

- Paste long‑form text or markdown
- Optional one‑line guidance (e.g., *"turn into an investor pitch deck"*)
- Upload a `.pptx` or `.potx` template/presentation (styles, colors, fonts, and layouts are reused)
- Reuse **images from your template** (no AI image generation)
- Choose provider + model; enter your own API key (never stored)
- Download a freshly generated `.pptx`

### Optional extras (if enabled)
- Auto‑generate speaker notes per slide (LLM)
- Heuristic fallback (works without an API key)

---

## Quick start

```bash
# 1) Create env & install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) Run the server
uvicorn app.main:app --reload

# 3) Open the UI
# http://localhost:8000
```

> **Privacy:** We do not store text, files, or API keys. All processing occurs in memory per request. Logs are minimized and never include keys.

---

## Design write‑up (200–300 words)

Parsing & mapping (what becomes a slide): When an API key is provided, the server prompts the chosen LLM to return a strict JSON outline: a deck title plus an ordered list of slides, each with a title, 1–6 concise bullets, an optional layout hint, and (if enabled) speaker notes. JSON‑mode output keeps the structure predictable and easy to validate. If you omit the key or a provider call fails, a deterministic fallback parser takes over. It reads your markdown headings as slide titles, converts list items into bullets, and chunks long paragraphs into slides of roughly 60–110 words. Very long lines are compressed, and bullets are capped to avoid overcrowding. The final outline typically lands between 8 and 25 slides, but adapts to the size and structure of the input.

Applying your visual style (fonts, colors, layouts, and images): The uploaded .pptx/.potx becomes the base Presentation, so generated slides inherit the template’s theme—masters, fonts, and colors—without attempting to recreate them manually. For layout selection, the app looks for familiar choices such as “Title and Content,” “Content with Caption,” or “Two Content,” then gracefully falls back to any available layout if names differ. To reuse visuals without generating new images, the app opens the template as a ZIP and reads ppt/media/* assets. During slide creation it prefers picture or content placeholders and inserts those template images in sequence; when no placeholder is available, the image is positioned in a sensible region (for example, the right column). Speaker notes, when requested, are inserted into the notes pane. The resulting .pptx is streamed back to the browser for immediate download. No text, files, or API keys are written to disk or logged.

---

## Supported providers

- **OpenAI** (`/v1/chat/completions` with `response_format={"type":"json_object"}`).
- **Anthropic** (`/v1/messages` with `anthropic-version` header).
- **Gemini** (`v1beta/models/*:generateContent`).
- **OpenAI‑compatible** (specify `Base URL`).

You control the **model name** and **API key**; neither is stored server‑side.

---

## Deployment

### Render.com (one‑click-ish)

1. Fork this repo.
2. Create a new **Web Service** on Render, connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set instance type and hit deploy. Your demo URL becomes public on first successful deploy.

### Docker

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Security & limits

- File types: `.pptx`, `.potx`
- Max template size: 20 MB (configurable in `app/config.py`)
- No persistent storage; no database
- Never logs API keys; minimal error messages

---

## License

[MIT](./LICENSE)
