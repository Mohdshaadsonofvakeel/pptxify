# app/template_utils.py
import zipfile
from io import BytesIO
from typing import List, Optional
from pptx import Presentation


def extract_template_images(template_bytes: bytes) -> List[bytes]:
    """
    Return raw image bytes in the uploaded PPTX template (ppt/media/*).
    """
    images: List[bytes] = []
    with zipfile.ZipFile(BytesIO(template_bytes)) as z:
        for name in sorted(z.namelist()):
            if name.startswith("ppt/media/"):
                with z.open(name) as f:
                    images.append(f.read())
    return images


def find_preferred_layout(prs: Presentation, preferred_names: List[str]) -> Optional["SlideLayout"]:
    # Try exact (case-insensitive) name matches first
    lower_pref = [p.lower() for p in preferred_names]
    for layout in prs.slide_layouts:
        if layout.name and layout.name.lower() in lower_pref:
            return layout
    # Fallback: fuzzy contains
    for layout in prs.slide_layouts:
        if any(p.lower() in (layout.name or "").lower() for p in preferred_names):
            return layout
    return None
