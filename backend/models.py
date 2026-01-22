from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class SlideChunk(BaseModel):
    slide_number: int
    title: Optional[str] = None
    bullets: List[str] = []
    notes: Optional[str] = None
    raw_text: str
    section: Optional[str] = None
    is_heading: bool = False
    level: int = 0


class EnrichmentItem(BaseModel):
    summary: str
    expansions: List[str]
    references: List[str] = []
    search_snippets: List[str] = []


class SlideEnrichment(BaseModel):
    slide_number: int
    title: Optional[str] = None
    raw_text: str
    section: Optional[str] = None
    enrichment: EnrichmentItem


class TopicNote(BaseModel):
    title: str
    slide_numbers: List[int]
    section: Optional[str] = None
    raw_text: str
    enrichment: EnrichmentItem


class GlobalNotes(BaseModel):
    overview: str
    knowledge_points: List[str]
    related_refs: List[str] = []


class ProcessResponse(BaseModel):
    slides: List[SlideEnrichment]
    global_notes: Optional[GlobalNotes] = None
    topics: Optional[List[TopicNote]] = None
