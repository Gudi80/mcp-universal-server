"""Input validation for llm.query: size limit + repo-paste heuristic."""
from __future__ import annotations

import re

HARD_LIMIT_BYTES = 102_400  # 100 KB

# Heuristics for detecting repo-paste attempts
_CODE_FENCE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_DEFINITION_PATTERN = re.compile(
    r"^\s*(def |class |function |const |let |var |import |from |#include)",
    re.MULTILINE,
)


def check_input(text: str) -> list[str]:
    """Validate LLM query input. Returns list of rejection reasons (empty if OK)."""
    reasons: list[str] = []

    byte_size = len(text.encode("utf-8"))
    if byte_size > HARD_LIMIT_BYTES:
        reasons.append(
            f"Input size {byte_size} bytes exceeds hard limit of {HARD_LIMIT_BYTES} bytes"
        )
        return reasons  # No point checking heuristics on oversized input

    # Heuristic: many code fences suggest a repo paste
    fences = _CODE_FENCE_PATTERN.findall(text)
    if len(fences) > 10:
        reasons.append(
            f"Input contains {len(fences)} code fences — suspected repo paste"
        )

    # Heuristic: many function/class definitions
    definitions = _DEFINITION_PATTERN.findall(text)
    if len(definitions) > 20:
        reasons.append(
            f"Input contains {len(definitions)} code definitions — suspected repo paste"
        )

    return reasons
