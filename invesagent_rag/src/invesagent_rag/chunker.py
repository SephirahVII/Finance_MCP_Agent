from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from invesagent_rag.policy_tags import classify_text
from invesagent_rag.schema import RagChunk, RagDocument


L1_RE = re.compile(r"^([一二三四五六七八九十]+)[、.．]\s*(.{2,80})$")
REPORT_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十]+章(?:\s+.{2,80})?$")
REPORT_SECTION_RE = re.compile(r"^第[一二三四五六七八九十]+节\s+(.{2,80})$")
L2_RE = re.compile(r"^[（(]([一二三四五六七八九十]+)[）)]\s*(.{2,80})$")
L3_RE = re.compile(r"^(?:\d+(?:\.\d+)*[、.．]?|第[一二三四五六七八九十]+[，,、])\s*(.{2,80})$")


@dataclass
class SectionState:
    level_1: str = ""
    level_2: str = ""
    level_3: str = ""

    @property
    def path(self) -> str:
        return " > ".join(value for value in (self.level_1, self.level_2, self.level_3) if value)

    def update(self, paragraph: str) -> None:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        first_line = lines[0] if lines else ""
        if REPORT_CHAPTER_RE.match(first_line) and len(lines) > 1 and len(lines[1]) <= 80:
            first_line = f"{first_line} {lines[1]}"
        if match := L1_RE.match(first_line):
            self.level_1 = first_line
            self.level_2 = ""
            self.level_3 = ""
        elif match := REPORT_CHAPTER_RE.match(first_line):
            self.level_1 = first_line
            self.level_2 = ""
            self.level_3 = ""
        elif match := REPORT_SECTION_RE.match(first_line):
            self.level_1 = first_line
            self.level_2 = ""
            self.level_3 = ""
        elif match := L2_RE.match(first_line):
            self.level_2 = first_line
            self.level_3 = ""
        elif match := L3_RE.match(first_line):
            self.level_3 = first_line


@dataclass
class TextUnit:
    text: str
    section: SectionState


def _split_long_paragraph(paragraph: str, size: int) -> list[str]:
    if len(paragraph) <= size:
        return [paragraph]
    pieces = re.split(r"(?<=[。！？；])", paragraph)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if len(current) + len(piece) <= size:
            current += piece
        else:
            if current:
                chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= size:
            final.append(chunk)
        else:
            final.extend(chunk[i : i + size] for i in range(0, len(chunk), size))
    return final


def _build_units(text: str, chunk_size: int) -> list[TextUnit]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    state = SectionState()
    units: list[TextUnit] = []
    for paragraph in paragraphs:
        state.update(paragraph)
        snapshot = SectionState(state.level_1, state.level_2, state.level_3)
        for piece in _split_long_paragraph(paragraph, chunk_size):
            units.append(TextUnit(piece, snapshot))
    return units


def chunk_document(document: RagDocument, chunk_size: int = 900, overlap: int = 120) -> list[RagChunk]:
    units = _build_units(document.text, chunk_size)
    chunks: list[tuple[str, SectionState]] = []
    current = ""
    current_section = SectionState()
    for unit in units:
        candidate = f"{current}\n\n{unit.text}".strip() if current else unit.text
        if len(candidate) <= chunk_size:
            current = candidate
            current_section = unit.section
            continue
        if current:
            chunks.append((current, current_section))
        prefix = current[-overlap:] if overlap > 0 and current else ""
        current = f"{prefix}\n\n{unit.text}".strip() if prefix else unit.text
        current_section = unit.section
    if current:
        chunks.append((current, current_section))

    result: list[RagChunk] = []
    for index, (text, section) in enumerate(chunks):
        stable = hashlib.sha1(f"{document.doc_id}:{index}:{text[:80]}".encode("utf-8")).hexdigest()
        tags = classify_text(f"{section.path}\n{text}", document.source_type)
        result.append(
            RagChunk(
                chunk_id=stable,
                doc_id=document.doc_id,
                chunk_index=index,
                text=text,
                title=document.title,
                source_type=document.source_type,
                source_name=document.source_name,
                source_path=document.source_path,
                jurisdiction_level=document.jurisdiction_level,
                region=document.region,
                year=document.year,
                published_at=document.published_at,
                market=document.market,
                url=document.url,
                topics=document.topics,
                symbol=document.symbol,
                company_name=document.company_name,
                report_year=document.report_year,
                report_type=document.report_type,
                section_level_1=section.level_1,
                section_level_2=section.level_2,
                section_level_3=section.level_3,
                section_path=section.path,
                content_categories=tags["content_categories"],
                policy_tools=tags["policy_tools"],
                mentioned_industries=tags["mentioned_industries"],
            )
        )
    return result
