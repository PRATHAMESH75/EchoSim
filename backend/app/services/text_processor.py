"""Text processing utilities."""

from typing import List
from ..utils.file_parser import FileParser, split_text_into_chunks


class TextProcessor:
    """Thin wrapper around FileParser and chunking helpers."""

    @staticmethod
    def extract_from_files(file_paths: List[str]) -> str:
        """Extract and concatenate text from multiple files."""
        return FileParser.extract_from_multiple(file_paths)

    @staticmethod
    def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for LLM processing."""
        return split_text_into_chunks(text, chunk_size, overlap)

    @staticmethod
    def preprocess_text(text: str) -> str:
        """Normalise whitespace and line endings."""
        import re

        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines).strip()

    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Return basic character/line/word counts."""
        return {
            "total_chars": len(text),
            "total_lines": text.count('\n') + 1,
            "total_words": len(text.split()),
        }
