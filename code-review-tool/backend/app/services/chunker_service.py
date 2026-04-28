"""Intelligent code chunking for large files.

Splits code at natural language-specific boundaries (function/class
definitions) so each chunk sent to Ollama is semantically coherent.
Falls back to blank-line splitting, then line-count splitting.
"""
import re
from dataclasses import dataclass

# ~3 000 tokens — comfortably within codellama's 4 096-token window
MAX_CHUNK_CHARS = 12_000

# Lookahead patterns so re.split keeps the boundary line in the following chunk
_BOUNDARY_PATTERNS: dict[str, re.Pattern[str]] = {
    "python":     re.compile(r"(?m)^(?=class |def |async def )", re.MULTILINE),
    "javascript": re.compile(r"(?m)^(?=function |class |export )", re.MULTILINE),
    "typescript": re.compile(r"(?m)^(?=function |class |export |interface |type )", re.MULTILINE),
    "go":         re.compile(r"(?m)^(?=func |type |var |const )", re.MULTILINE),
    "rust":       re.compile(r"(?m)^(?=pub fn |fn |impl |pub struct |struct |pub enum |enum |pub trait |trait )", re.MULTILINE),
    "java":       re.compile(r"(?m)^(?=\s*(?:public|private|protected|static)\s+\w)", re.MULTILINE),
    "kotlin":     re.compile(r"(?m)^(?=fun |class |object |interface )", re.MULTILINE),
    "ruby":       re.compile(r"(?m)^(?=def |class |module )", re.MULTILINE),
    "csharp":     re.compile(r"(?m)^(?=\s*(?:public|private|protected|static|override|virtual)\s+\w)", re.MULTILINE),
    "swift":      re.compile(r"(?m)^(?=func |class |struct |enum |extension |protocol )", re.MULTILINE),
    "scala":      re.compile(r"(?m)^(?=def |class |object |trait )", re.MULTILINE),
    "php":        re.compile(r"(?m)^(?=function |class )", re.MULTILINE),
}

_BLANK_LINE = re.compile(r"\n\n+")


@dataclass
class CodeChunk:
    content: str
    chunk_index: int
    total_chunks: int
    filename: str


def chunk_code(
    code: str,
    filename: str,
    language: str = "unknown",
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[CodeChunk]:
    """Split *code* into chunks that each fit within *max_chars*.

    Splitting priority:
    1. Language-specific boundary pattern (function/class definitions)
    2. Blank lines
    3. Individual lines

    Each chunk preserves the original text exactly — concatenating all
    ``chunk.content`` values reproduces the original *code* string.
    """
    if len(code) <= max_chars:
        return [CodeChunk(content=code, chunk_index=1, total_chunks=1, filename=filename)]

    sections = _split_into_sections(code, language)
    chunks_text = _pack_sections(sections, max_chars)

    total = len(chunks_text)
    return [
        CodeChunk(content=text, chunk_index=i + 1, total_chunks=total, filename=filename)
        for i, text in enumerate(chunks_text)
    ]


def format_chunk_for_review(chunk: CodeChunk) -> str:
    """Prepend a context header when the file was split into multiple chunks."""
    if chunk.total_chunks == 1:
        return chunk.content
    header = f"# File: {chunk.filename} (chunk {chunk.chunk_index} of {chunk.total_chunks})\n\n"
    return header + chunk.content


# ── Internal helpers ──────────────────────────────────────────────────────────

def _split_into_sections(code: str, language: str) -> list[str]:
    """Return code split at logical boundaries for the given language."""
    pattern = _BOUNDARY_PATTERNS.get(language)
    if pattern:
        parts = re.split(pattern, code)
        if len(parts) > 1:
            return [p for p in parts if p]  # drop empty strings from split

    # Blank-line fallback
    parts = re.split(_BLANK_LINE, code)
    if len(parts) > 1:
        # Re-add the separating blank lines so concatenation is lossless
        reconstructed: list[str] = []
        remaining = code
        for part in parts:
            idx = remaining.find(part)
            if idx > 0:
                reconstructed.append(remaining[:idx])  # the blank lines
            reconstructed.append(part)
            remaining = remaining[idx + len(part):]
        if remaining:
            reconstructed.append(remaining)
        return [s for s in reconstructed if s]

    # Last resort: split by lines
    return _split_by_lines(code)


def _split_by_lines(code: str) -> list[str]:
    return code.splitlines(keepends=True)


def _pack_sections(sections: list[str], max_chars: int) -> list[str]:
    """Greedily pack sections into chunks that each fit within *max_chars*.

    Sections that individually exceed *max_chars* are further split by
    character slices so that no output chunk is left unbounded.
    """
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for section in sections:
        # If this single section already exceeds max_chars, slice it directly.
        if len(section) > max_chars:
            if current_parts:
                chunks.append("".join(current_parts))
                current_parts = []
                current_len = 0
            for start in range(0, len(section), max_chars):
                chunks.append(section[start: start + max_chars])
            continue

        section_len = len(section)
        if current_len + section_len > max_chars and current_parts:
            chunks.append("".join(current_parts))
            current_parts = [section]
            current_len = section_len
        else:
            current_parts.append(section)
            current_len += section_len

    if current_parts:
        chunks.append("".join(current_parts))

    return chunks or ["".join(sections)]
