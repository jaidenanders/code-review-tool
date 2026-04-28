"""TDD tests for ChunkerService — intelligent code splitting."""
import pytest
from app.services.chunker_service import (
    chunk_code,
    format_chunk_for_review,
    CodeChunk,
    MAX_CHUNK_CHARS,
)


def make_code(lines: int, line_width: int = 80) -> str:
    return "\n".join(f"x = {i}" + " " * (line_width - 6) for i in range(lines))


class TestChunkCode:
    def test_small_code_returns_single_chunk(self):
        code = "def foo():\n    return 1\n"
        chunks = chunk_code(code, "test.py", "python")
        assert len(chunks) == 1
        assert chunks[0].content == code

    def test_single_chunk_has_correct_metadata(self):
        code = "x = 1\n"
        chunks = chunk_code(code, "script.py", "python")
        assert chunks[0].chunk_index == 1
        assert chunks[0].total_chunks == 1
        assert chunks[0].filename == "script.py"

    def test_large_code_produces_multiple_chunks(self):
        # Build code that clearly exceeds MAX_CHUNK_CHARS
        code = "\n".join(
            [f"def func_{i}():\n    return {i}\n" for i in range(500)]
        )
        assert len(code) > MAX_CHUNK_CHARS
        chunks = chunk_code(code, "big.py", "python")
        assert len(chunks) > 1

    def test_no_chunk_exceeds_max_chars(self):
        code = "\n".join(
            [f"def func_{i}():\n    return {i}\n" for i in range(500)]
        )
        chunks = chunk_code(code, "big.py", "python", max_chars=MAX_CHUNK_CHARS)
        for chunk in chunks:
            assert len(chunk.content) <= MAX_CHUNK_CHARS * 1.5  # allow one section to overflow

    def test_chunk_indices_are_sequential(self):
        code = "\n".join(
            [f"def func_{i}():\n    return {i}\n" for i in range(500)]
        )
        chunks = chunk_code(code, "big.py", "python")
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(1, len(chunks) + 1))

    def test_all_chunks_have_same_total(self):
        code = "\n".join(
            [f"def func_{i}():\n    return {i}\n" for i in range(500)]
        )
        chunks = chunk_code(code, "big.py", "python")
        totals = {c.total_chunks for c in chunks}
        assert len(totals) == 1
        assert list(totals)[0] == len(chunks)

    def test_no_data_loss_python(self):
        """Reassembled chunks should contain all original content."""
        code = "\n".join(
            [f"def func_{i}():\n    x = {i}\n    return x\n" for i in range(300)]
        )
        chunks = chunk_code(code, "big.py", "python")
        reassembled = "".join(c.content for c in chunks)
        assert reassembled == code

    def test_python_splits_at_def_boundaries(self):
        # Two large defs that together exceed max_chars
        single_def = "def big_function():\n" + "    x = 1\n" * 1000
        code = single_def + "\n" + single_def  # two defs
        chunks = chunk_code(code, "a.py", "python", max_chars=len(single_def) + 50)
        # Should split into at least 2 chunks (one per def)
        assert len(chunks) >= 2
        # Each chunk should start with the def
        assert chunks[0].content.lstrip().startswith("def big_function")

    def test_typescript_splits_at_function_boundaries(self):
        single_fn = "export function bigFn(): void {\n" + "  console.log('x');\n" * 600 + "}\n"
        code = single_fn + "\n" + single_fn
        chunks = chunk_code(code, "a.ts", "typescript", max_chars=len(single_fn) + 50)
        assert len(chunks) >= 2

    def test_go_splits_at_func_boundaries(self):
        single_fn = "func BigFunc() {\n" + "\tx := 1\n" * 600 + "}\n"
        code = single_fn + "\n" + single_fn
        chunks = chunk_code(code, "main.go", "go", max_chars=len(single_fn) + 50)
        assert len(chunks) >= 2

    def test_unknown_language_falls_back_gracefully(self):
        code = "A" * (MAX_CHUNK_CHARS * 3)
        chunks = chunk_code(code, "file.xyz", "unknown")
        assert len(chunks) > 1

    def test_custom_max_chars(self):
        code = "x = 1\n" * 100
        chunks = chunk_code(code, "tiny.py", "python", max_chars=50)
        assert len(chunks) > 1

    def test_filename_stored_on_each_chunk(self):
        code = "\n".join([f"def f{i}():\n    pass\n" for i in range(400)])
        chunks = chunk_code(code, "myfile.py", "python")
        for c in chunks:
            assert c.filename == "myfile.py"


class TestFormatChunkForReview:
    def test_single_chunk_has_no_header(self):
        chunk = CodeChunk(content="x = 1", chunk_index=1, total_chunks=1, filename="f.py")
        assert format_chunk_for_review(chunk) == "x = 1"

    def test_multi_chunk_has_header(self):
        chunk = CodeChunk(content="x = 1", chunk_index=2, total_chunks=3, filename="f.py")
        result = format_chunk_for_review(chunk)
        assert "f.py" in result
        assert "chunk 2 of 3" in result
        assert "x = 1" in result

    def test_header_precedes_content(self):
        chunk = CodeChunk(content="code here", chunk_index=1, total_chunks=2, filename="app.ts")
        result = format_chunk_for_review(chunk)
        header_end = result.index("code here")
        assert header_end > 0  # header comes first
