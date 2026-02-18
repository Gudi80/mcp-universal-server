"""review_pr prompt — structured code review template."""
from __future__ import annotations

from typing import Any

from src.core.config import AppConfig
from src.core.types import PluginManifest
from src.plugins._base import PromptPlugin

_TEMPLATE = """You are a senior software engineer performing a code review.

## Diff to review:
```{language}
{diff}
```

## Instructions:
1. Identify bugs, security issues, and performance problems.
2. Check for adherence to coding standards and best practices.
3. Suggest concrete improvements with code examples where appropriate.
4. Note any missing error handling or edge cases.
5. Comment on code readability and maintainability.

Provide your review as a structured list of findings, each with:
- **Severity**: critical / warning / suggestion
- **Location**: file and line if identifiable
- **Issue**: description
- **Fix**: recommended change
"""


class ReviewPRPlugin(PromptPlugin):
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="prompt.review_pr",
            title="Review PR",
            description="Code review prompt: provide a diff and language to get structured feedback.",
        )

    def prompt_name(self) -> str:
        return "review_pr"

    def arguments(self) -> list[dict[str, Any]]:
        return [
            {"name": "diff", "description": "The code diff to review", "required": True},
            {"name": "language", "description": "Programming language (e.g. python, typescript)", "required": False},
        ]

    async def render(self, args: dict[str, str]) -> str:
        diff = args.get("diff", "")
        language = args.get("language", "")
        return _TEMPLATE.format(diff=diff, language=language)


def create_plugin(**kwargs: Any) -> ReviewPRPlugin:
    return ReviewPRPlugin()
