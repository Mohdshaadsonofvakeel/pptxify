# app/schemas.py
from typing import List, Optional
from pydantic import BaseModel


class OutlineSlide(BaseModel):
    title: str
    bullets: List[str]
    layout: str = "auto"
    notes: Optional[str] = None


class Outline(BaseModel):
    title: str
    slides: List[OutlineSlide]
    estimated_slide_count: int
