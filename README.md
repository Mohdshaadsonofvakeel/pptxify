# pptxify — Your Text, Your Style

Create a publicly accessible web app that turns bulk text or markdown into a fully formatted PowerPoint
that matches an uploaded template’s look and feel. Keys are never stored; images are reused only from the template.

## Quick start

```bash
pip install -r pptxify/requirements.txt
uvicorn pptxify.app.main:app --reload
# open http://localhost:8000
```

## Requirements implemented
- Paste large text/markdown
- Optional one-line guidance
- User-supplied API key + provider (OpenAI/Anthropic/Gemini/OpenAI-compatible)
- Upload `.pptx`/`.potx`, download generated `.pptx`
- Intelligent mapping to slide count (via LLM or robust heuristic fallback)
- Reuse template styles/layouts; reuse embedded images (no AI image generation)
- MIT license & README

## Notes
- API keys are not persisted or logged. No database. Minimal error messages.
- File size limit configurable in `pptxify/app/config.py`.

## Design write-up (approx. 250 words)
**Parsing & mapping.** When an API key is provided, the backend calls the selected LLM with a strict JSON schema
prompt that asks for a slide outline (title, bullets, optional notes, and a layout hint). We bias towards concise,
faithful bullet points built from the user’s text and we honor the optional guidance (e.g., *investor pitch*).
If the LLM call fails or no key is supplied, a markdown-aware heuristic fallback kicks in: headings start new slides,
lists become bullets, and long paragraphs are sentence-chunked into 60–110 words per slide. The result is validated
against a Pydantic schema before building slides.

**Applying visual style & assets.** We open the uploaded PowerPoint template using `python-pptx` and always add new
slides using the template’s own layouts (Title and Content, Section Header, etc.). Titles and bullets are written
into the matching placeholders so the template’s fonts, colors, and spacing carry over automatically. We also surface
any embedded images from `ppt/media/*` and (optionally) drop one onto every 3rd slide as a tasteful accent, ensuring
we never generate new images. Speaker notes are added when requested. The final `.pptx` is streamed to the browser;
nothing is stored server-side.

## Deploy
- Any ASGI host (Render, Railway, Fly, etc.). Provide environment variables for default models if desired.
