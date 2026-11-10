"""Document parsing (Markdown / HTML / PDF) and heading-aware chunking with overlap."""

import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePath
from typing import ClassVar

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf"}

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"(])")


@dataclass(frozen=True)
class Section:
    heading: str  # breadcrumb, e.g. "Retries > Dead-letter queue"
    text: str


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    heading: str
    text: str

    @property
    def indexed_text(self) -> str:
        """What gets embedded and full-text indexed: breadcrumb + body (contextual header)."""
        return f"{self.heading}\n{self.text}" if self.heading else self.text


# ---------- parsing ----------


def parse_markdown(text: str) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append(Section(" > ".join(t for _, t in stack), body))
        buf.clear()

    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).strip()))
        else:
            buf.append(line)
    flush()
    return sections


class _HTMLToMarkdown(HTMLParser):
    BLOCK: ClassVar = {"p", "div", "li", "pre", "tr", "br", "section", "article", "table", "ul", "ol"}
    SKIP: ClassVar = {"script", "style", "head", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in self.BLOCK:
            self.out.append("\n\n" + ("- " if tag == "li" else ""))

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif re.fullmatch(r"h[1-6]", tag) or tag in self.BLOCK:
            self.out.append("\n\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(re.sub(r"\s+", " ", data))


def parse_html(text: str) -> list[Section]:
    parser = _HTMLToMarkdown()
    parser.feed(text)
    md = "".join(parser.out)
    # Heading lines must not carry leading spaces, and paragraphs collapse to one blank line.
    md = re.sub(r"\n[ \t]+", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return parse_markdown(md)


def parse_pdf(data: bytes, title: str) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    sections = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(Section(f"{title} > page {i}", text))
    return sections


def parse_document(filename: str, data: bytes) -> list[Section]:
    ext = PurePath(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext or filename}")
    if ext == ".pdf":
        return parse_pdf(data, PurePath(filename).stem)
    text = data.decode("utf-8", errors="replace")
    if ext in {".html", ".htm"}:
        return parse_html(text)
    return parse_markdown(text)


# ---------- chunking ----------


def _split_long(paragraph: str, max_chars: int) -> list[str]:
    """Split an over-long paragraph on sentence boundaries, hard-splitting as a last resort."""
    pieces, cur = [], ""
    for sent in _SENTENCE_END.split(paragraph):
        while len(sent) > max_chars:
            pieces.append(sent[:max_chars])
            sent = sent[max_chars:]
        if cur and len(cur) + 1 + len(sent) > max_chars:
            pieces.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def _tail(text: str, n: int) -> str:
    """Last ~n characters of text, starting on a word boundary."""
    if n <= 0 or len(text) <= n:
        return text if n > 0 else ""
    cut = text[-n:]
    space = cut.find(" ")
    return cut[space + 1 :] if space != -1 else cut


def chunk_sections(sections: list[Section], max_chars: int = 800, overlap: int = 120) -> list[Chunk]:
    """Pack paragraphs into chunks of <= max_chars without crossing section boundaries.

    Consecutive chunks of the same section share ~`overlap` characters so a fact that
    straddles a boundary is still retrievable from either side.
    """
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")
    chunks: list[Chunk] = []
    for section in sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section.text) if p.strip()]
        units = [u for p in paragraphs for u in _split_long(p, max_chars - overlap)]
        cur = ""
        for unit in units:
            if cur and len(cur) + 2 + len(unit) > max_chars:
                chunks.append(Chunk(len(chunks), section.heading, cur))
                cur = _tail(cur, overlap)
            cur = f"{cur}\n\n{unit}" if cur else unit
        if cur:
            chunks.append(Chunk(len(chunks), section.heading, cur))
    return chunks


def chunk_document(filename: str, data: bytes, max_chars: int = 800, overlap: int = 120) -> list[Chunk]:
    return chunk_sections(parse_document(filename, data), max_chars, overlap)
