from itertools import pairwise

import pytest

from ragdesk.chunker import Section, chunk_document, chunk_sections, parse_html, parse_markdown

from .conftest import make_pdf


def test_markdown_headings_become_breadcrumbs():
    md = "# Guide\nintro\n## Install\nrun it\n### Linux\napt\n## Usage\nuse it\n"
    assert parse_markdown(md) == [
        Section("Guide", "intro"),
        Section("Guide > Install", "run it"),
        Section("Guide > Install > Linux", "apt"),
        Section("Guide > Usage", "use it"),
    ]


def test_hash_lines_inside_code_fences_are_not_headings():
    md = "# Setup\n```\n# not a heading\necho hi\n```\n"
    [section] = parse_markdown(md)
    assert section.heading == "Setup"
    assert "# not a heading" in section.text


def test_chunks_respect_size_and_overlap():
    words = " ".join(f"word{i}" for i in range(400))  # ~3.3k chars, single paragraph
    chunks = chunk_sections([Section("H", words)], max_chars=500, overlap=100)
    assert len(chunks) > 5
    assert all(len(c.text) <= 500 for c in chunks)
    for a, b in pairwise(chunks):
        shared = a.text[-60:].split()[-1]
        assert shared in b.text[:120], "consecutive chunks should overlap"
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_chunks_never_cross_sections():
    sections = [Section("A", "alpha " * 10), Section("B", "beta " * 10)]
    chunks = chunk_sections(sections, max_chars=800, overlap=100)
    assert [(c.heading, c.text.split()[0]) for c in chunks] == [("A", "alpha"), ("B", "beta")]


def test_indexed_text_includes_heading_context():
    [chunk] = chunk_sections([Section("Retries > Backoff", "doubles each time")])
    assert chunk.indexed_text == "Retries > Backoff\ndoubles each time"


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_sections([Section("A", "x")], max_chars=100, overlap=100)


def test_html_parsing_keeps_headings_and_drops_scripts():
    html = (
        "<html><head><title>T</title><style>p{}</style></head><body>"
        "<h1>API</h1><p>Intro text.</p><script>alert('x')</script>"
        "<h2>Auth</h2><ul><li>Use a token</li><li>Rotate it</li></ul></body></html>"
    )
    sections = parse_html(html)
    assert [s.heading for s in sections] == ["API", "API > Auth"]
    assert "alert" not in "".join(s.text for s in sections)
    assert "- Use a token" in sections[1].text


def test_pdf_text_is_extracted_per_page():
    chunks = chunk_document("manual.pdf", make_pdf("Kestrel supports PDF ingestion"))
    assert len(chunks) == 1
    assert chunks[0].heading == "manual > page 1"
    assert "PDF ingestion" in chunks[0].text


def test_unsupported_extension_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        chunk_document("photo.png", b"\x89PNG")
