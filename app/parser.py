# app/parser.py
"""
Heuristic fallback parser that maps raw text/markdown into a slide outline if no LLM is used,
or if the provider request fails.
"""
import re
from typing import Dict, List, Any
from markdown_it import MarkdownIt

MAX_BULLETS = 6
MAX_CHARS_PER_BULLET = 120
WORDS_PER_SLIDE = (60, 110)  # min, max


def _split_words(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _truncate(s: str, n: int) -> str:
    s = _collapse_ws(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def heuristic_outline(text: str, guidance: str = "", include_notes: bool = False) -> Dict[str, Any]:
    md = MarkdownIt()
    tokens = md.parse(text or "")
    slides: List[Dict[str, Any]] = []
    cur_title = None
    cur_bullets: List[str] = []

    def flush():
        nonlocal cur_title, cur_bullets
        if cur_title or cur_bullets:
            slides.append({
                "title": cur_title or "Overview",
                "bullets": cur_bullets[:MAX_BULLETS] or [],
                **({"notes": ""} if include_notes else {}),
                "layout": "auto"
            })
        cur_title, cur_bullets = None, []

    # Simple markdown-aware parse
    for t in tokens:
        if t.type == "heading_open":
            # next token should be the text (inline)
            flush()
        elif t.type == "inline":
            # heading text or paragraph list items
            # detect heading by presence of 'map' attribute from previous heading_open
            if t.map and tokens[max(0, tokens.index(t) - 1)].type == "heading_open":
                cur_title = _truncate(t.content, 80)
            else:
                # bullet lines starting with - or * in raw
                lines = [ln.strip() for ln in t.content.split("\n") if ln.strip()]
                for ln in lines:
                    # ignore images/links markup
                    ln = re.sub(r"!\[.*?\]\(.*?\)", "", ln)
                    ln = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", ln)
                    if ln.startswith(("-", "*", "•")):
                        ln = ln.lstrip("-*• ").strip()
                    cur_bullets.append(_truncate(ln, MAX_CHARS_PER_BULLET))
        elif t.type == "paragraph_open":
            # paragraph as a bullet if we have a title
            pass
        elif t.type == "paragraph_close":
            pass

    flush()

    # If no headings at all, chunk by words
    if all(s["title"] == "Overview" for s in slides):
        words = re.split(r"\s+", _collapse_ws(text))
        approx = max(1, min(25, len(words) // ((WORDS_PER_SLIDE[0] + WORDS_PER_SLIDE[1]) // 2)))
        # Create approx slides by grouping sentences
        sentences = re.split(r"(?<=[.!?])\s+", _collapse_ws(text))
        sentence_groups = list(_chunks(sentences, max(1, len(sentences)//approx)))
        slides = []
        for i, group in enumerate(sentence_groups, 1):
            bul = []
            for sent in group:
                sent = _truncate(sent, MAX_CHARS_PER_BULLET)
                if sent:
                    bul.append(sent)
            slides.append({
                "title": f"Section {i}",
                "bullets": bul[:MAX_BULLETS],
                **({"notes": ""} if include_notes else {}),
                "layout": "auto"
            })

    title = "Generated Presentation"
    if guidance:
        title = f"{title} – {guidance[:60]}"

    return {
        "title": title,
        "slides": slides[:30],
        "estimated_slide_count": len(slides[:30])
    }
