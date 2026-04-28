"""Language detection from file extensions."""
from pathlib import Path

_EXT_MAP: dict[str, str] = {
    # Python
    ".py": "python", ".pyi": "python",
    # JavaScript
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    # TypeScript
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    # Systems
    ".rs": "rust",
    ".go": "go",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".zig": "zig",
    # JVM
    ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".groovy": "groovy",
    # .NET
    ".cs": "csharp",
    ".fs": "fsharp",
    ".vb": "vbnet",
    # Scripting
    ".rb": "ruby",
    ".php": "php",
    ".pl": "perl", ".pm": "perl",
    ".lua": "lua",
    ".r": "r",
    ".jl": "julia",
    ".nim": "nim",
    # Shell
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "bash",
    ".ps1": "powershell",
    # Mobile
    ".swift": "swift",
    ".dart": "dart",
    # Functional
    ".hs": "haskell",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".ml": "ocaml",
    ".clj": "clojure", ".cljs": "clojure",
    # Web
    ".html": "html", ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    # Data / config
    ".sql": "sql",
    ".graphql": "graphql", ".gql": "graphql",
    ".proto": "protobuf",
    ".tf": "terraform", ".hcl": "terraform",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".md": "markdown", ".mdx": "markdown",
}


def detect_language(filename: str) -> str:
    """Return the programming language for *filename* based on its extension.

    Returns ``"unknown"`` for unrecognised or missing extensions.
    """
    if not filename:
        return "unknown"
    ext = Path(filename).suffix.lower()
    if not ext:
        return "unknown"
    return _EXT_MAP.get(ext, "unknown")
