# app/main.py
import io
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .pptx_builder import build_presentation
from .parser import heuristic_outline
from .llm_clients import plan_slides_via_llm
from .schemas import Outline, OutlineSlide
from .config import MAX_FILE_MB, ALLOWED_EXTS, DEFAULT_MODEL, DEFAULT_PROVIDER

app = FastAPI(title="pptxify", version="1.0.0", docs_url="/docs")

# Serve the static front-end
static_path = os.path.join(os.path.dirname(__file__), "..", "web")
app.mount("/assets", StaticFiles(directory=static_path), name="assets")


@app.get("/", response_class=HTMLResponse)
def index():
    index_html_path = os.path.join(static_path, "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}


@app.post("/api/generate")
async def generate_pptx(
    text: str = Form(..., description="Raw text or markdown input"),
    guidance: Optional[str] = Form(None, description="Optional one-line guidance"),
    provider: str = Form(DEFAULT_PROVIDER, description="LLM provider name"),
    model: Optional[str] = Form(DEFAULT_MODEL, description="Model name for the provider"),
    api_key: Optional[str] = Form(None, description="User-supplied LLM API key (never stored)"),
    base_url: Optional[str] = Form(None, description="Base URL for OpenAI-compatible providers (optional)"),
    include_notes: Optional[bool] = Form(False, description="If true, auto-generate speaker notes per slide"),
    template: UploadFile = File(..., description="PowerPoint template or presentation (.pptx or .potx)"),
):
    # Validate template ext and size
    name = template.filename or "template.pptx"
    ext = os.path.splitext(name.lower())[1]
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTS)}")

    contents = await template.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"Template too large ({size_mb:.1f} MB). Max is {MAX_FILE_MB} MB.")

    # Build an outline using LLM if key is provided, else a local heuristic fallback
    try:
        if api_key and provider:
            outline_dict = plan_slides_via_llm(
                text=text,
                guidance=guidance or "",
                provider=provider,
                api_key=api_key,
                model=model or "",
                base_url=base_url,
                include_notes=bool(include_notes),
            )
        else:
            outline_dict = heuristic_outline(text=text, guidance=guidance or "", include_notes=bool(include_notes))
    except Exception as e:
        # Defensive fallback if provider errors, never leak key
        outline_dict = heuristic_outline(text=text, guidance=guidance or "", include_notes=bool(include_notes))

    # Validate structure
    outline = Outline(**outline_dict)

    # Build PPTX bytes
    try:
        pptx_bytes = build_presentation(outline=outline, template_bytes=contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build PowerPoint: {e}")

    # Stream back as a file download
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"pptxify-{ts}.pptx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return StreamingResponse(io.BytesIO(pptx_bytes),
                              media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                              headers=headers)
