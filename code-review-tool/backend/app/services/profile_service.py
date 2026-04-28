"""Review profiles — focused prompt instructions for different review lenses."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReviewProfile:
    id: str
    name: str
    description: str
    focus_instructions: str


PROFILES: dict[str, ReviewProfile] = {
    "general": ReviewProfile(
        id="general",
        name="General",
        description="Balanced review covering bugs, style, security, and performance.",
        focus_instructions="",
    ),
    "security": ReviewProfile(
        id="security",
        name="Security",
        description="Deep-dive into vulnerabilities, injection flaws, authentication, and secrets.",
        focus_instructions=(
            "FOCUS: Security review. Prioritise injection vulnerabilities (SQL, command, XSS), "
            "authentication and authorisation flaws, hard-coded secrets or credentials, insecure "
            "deserialisation, path traversal, and missing input validation. "
            "Score harshly on any security issue found."
        ),
    ),
    "performance": ReviewProfile(
        id="performance",
        name="Performance",
        description="Focus on algorithmic complexity, memory usage, and runtime bottlenecks.",
        focus_instructions=(
            "FOCUS: Performance review. Prioritise algorithmic complexity (O(n²) or worse), "
            "N+1 query patterns, unnecessary re-computation, blocking I/O in async contexts, "
            "memory leaks, and missing caching opportunities. "
            "Score harshly on performance issues."
        ),
    ),
    "style": ReviewProfile(
        id="style",
        name="Style",
        description="Focus on readability, naming conventions, and code organisation.",
        focus_instructions=(
            "FOCUS: Code style review. Prioritise naming clarity (variables, functions, classes), "
            "function length and single-responsibility, code duplication, comment quality, "
            "consistent formatting, and overall readability. "
            "Score harshly on style and clarity issues."
        ),
    ),
}

# Insertion-order guaranteed in Python 3.7+, so general is always first.
_PROFILE_ORDER = ["general", "security", "performance", "style"]


def get_profile(profile_id: Optional[str]) -> ReviewProfile:
    """Return the named profile, falling back to general for unknown/None ids."""
    if profile_id is None:
        return PROFILES["general"]
    return PROFILES.get(profile_id, PROFILES["general"])


def list_profiles() -> list[ReviewProfile]:
    """Return all profiles in display order (general first)."""
    return [PROFILES[pid] for pid in _PROFILE_ORDER]
