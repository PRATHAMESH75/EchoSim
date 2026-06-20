"""Tests for TextProcessor whitespace/normalisation helpers (issue #26)."""

from app.services.text_processor import TextProcessor


def test_preprocess_normalises_line_endings_and_trims():
    text = "  hello \r\n world  \r\n\r\n\r\n end  "
    result = TextProcessor.preprocess_text(text)
    # CRLF/CR -> LF, per-line trim, 3+ blank lines collapsed to one blank line.
    assert "\r" not in result
    assert result == "hello\nworld\n\nend"


def test_preprocess_collapses_excess_blank_lines():
    assert TextProcessor.preprocess_text("a\n\n\n\n\nb") == "a\n\nb"


def test_split_text_returns_whole_text_when_short():
    assert TextProcessor.split_text("short", chunk_size=500) == ["short"]


def test_split_text_chunks_long_text():
    text = "word " * 400  # 2000 chars, no sentence separators
    chunks = TextProcessor.split_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_get_text_stats_counts():
    stats = TextProcessor.get_text_stats("one two\nthree")
    assert stats["total_words"] == 3
    assert stats["total_lines"] == 2
    assert stats["total_chars"] == len("one two\nthree")
