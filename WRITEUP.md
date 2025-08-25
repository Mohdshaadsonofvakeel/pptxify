# Design write-up (short)

**Parsing & mapping:** If a user provides an API key, we prompt the chosen model to output a strict JSON outline (deck title, slide list with titles, bullets, optional layout, and optional speaker notes). If no key is provided or the call fails, we use a deterministic Markdown-aware parser that collects headings as slide titles, converts list items to bullets, and chunks prose into ~60–110 words per slide. We cap bullets to six per slide and compress overly long lines.

**Styling & assets:** We load the uploaded `.pptx/.potx` as the base `Presentation`, so all new slides inherit the template’s theme (masters, fonts, colors). We select familiar layouts by name ("Title and Content", "Content with Caption", "Two Content"), but gracefully fall back to any available layout if names differ. We reuse visuals by reading the template’s `ppt/media/*` images from the ZIP package and inserting them into picture or content placeholders on generated slides; otherwise we right‑align them when reasonable. No new images are generated.

**Output:** We insert slide titles and bullets into their respective placeholders and (optionally) speaker notes into the notes pane. The completed `.pptx` is streamed to the client for download. No data or keys are stored or logged.
