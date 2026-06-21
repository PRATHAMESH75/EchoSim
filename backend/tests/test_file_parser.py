"""Tests for file parsing + chunking utilities (issue #26)."""

import pytest

from app.utils.file_parser import FileParser, split_text_into_chunks


# --- split_text_into_chunks --------------------------------------------------

def test_short_text_is_single_chunk():
    assert split_text_into_chunks("hello world", chunk_size=500) == ["hello world"]


def test_blank_text_yields_no_chunks():
    assert split_text_into_chunks("   ", chunk_size=500) == []


def test_long_text_splits_into_multiple_chunks():
    text = "x" * 1200
    chunks = split_text_into_chunks(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 3
    assert all(chunks)


def test_splits_prefer_sentence_boundaries():
    # Two long sentences separated by a period+space; the first chunk should end
    # at the sentence boundary rather than mid-word.
    first = "a" * 400 + ". "
    second = "b" * 400 + "."
    chunks = split_text_into_chunks(first + second, chunk_size=500, overlap=10)
    assert chunks[0].endswith(".")


def test_chunks_overlap_preserves_content_order():
    text = "".join(chr(ord("a") + (i % 26)) for i in range(1500))
    chunks = split_text_into_chunks(text, chunk_size=400, overlap=50)
    # Reconstructed (de-overlapped) text should still contain the start and end.
    assert text[:10] in chunks[0]
    assert text[-10:] in chunks[-1]


# --- FileParser.extract_text -------------------------------------------------

def test_extract_text_reads_txt(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("plain text body", encoding="utf-8")
    assert FileParser.extract_text(str(path)) == "plain text body"


def test_extract_text_reads_markdown(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text("# Title\n\nbody", encoding="utf-8")
    assert "Title" in FileParser.extract_text(str(path))


def test_extract_text_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        FileParser.extract_text(str(tmp_path / "nope.txt"))


def test_extract_text_unsupported_extension_raises(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("a,b", encoding="utf-8")
    with pytest.raises(ValueError):
        FileParser.extract_text(str(path))


def test_extract_text_handles_non_utf8_encoding(tmp_path):
    path = tmp_path / "latin.txt"
    path.write_bytes("café résumé".encode("latin-1"))
    # Falls back to a detected encoding rather than raising.
    result = FileParser.extract_text(str(path))
    assert "caf" in result and "sum" in result


def test_extract_from_multiple_merges_and_tolerates_failures(tmp_path):
    good = tmp_path / "a.txt"
    good.write_text("first doc", encoding="utf-8")
    merged = FileParser.extract_from_multiple([str(good), str(tmp_path / "missing.txt")])
    assert "first doc" in merged
    assert "extraction failed" in merged  # missing file reported, not raised
