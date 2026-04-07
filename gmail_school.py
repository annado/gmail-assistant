"""Prepare school email summaries — cache emails and return context + file paths."""

from pathlib import Path
from typing import Any

from context_config import PersonalContext
from gmail_cache import ensure_cached

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _format_child(child: "ChildContext") -> str:
    """Format a single child's context."""
    lines = []
    if child.name:
        lines.append(f"Child: {child.name}")
    if child.grade:
        lines.append(f"Grade: {child.grade}")
    if child.level:
        lines.append(f"Level: {child.level}")
    if child.school:
        lines.append(f"School: {child.school}")
    if child.school_domain:
        lines.append(f"School email domain: {child.school_domain}")
    if child.division:
        lines.append(f"Division: {child.division}")
    if child.sports:
        lines.append(f"Sports: {', '.join(child.sports)}")
    if child.activities:
        lines.append(f"Activities: {', '.join(child.activities)}")
    if child.teachers:
        for t in child.teachers:
            lines.append(f"Teacher: {t}")
    return "\n".join(lines)


def _format_personal_context(ctx: PersonalContext) -> str:
    """Format personal context as a readable block."""
    if not ctx.children:
        return "No personal context configured."

    blocks = [_format_child(child) for child in ctx.children if child.name]
    return "\n\n".join(blocks) if blocks else "No personal context configured."


def _load_summary_instructions() -> str | None:
    """Load the school summary prompt template, or None if absent."""
    prompt_file = _PROMPTS_DIR / "school_summary.md"
    if not prompt_file.exists():
        return None
    try:
        return prompt_file.read_text().strip()
    except OSError:
        return None


def prepare_school_summary(
    service: Any,
    message_ids: list[str],
    context: PersonalContext,
) -> str:
    """Cache school emails and return personal context + file paths for Claude to read.

    Returns a short string with:
    - PERSONAL CONTEXT section
    - SUMMARY INSTRUCTIONS section (if prompt file exists)
    - EMAIL FILES section with absolute paths to cached markdown files
    """
    if not message_ids:
        return "No message IDs provided."

    sections = []

    # Personal context
    sections.append("=== PERSONAL CONTEXT ===")
    sections.append(_format_personal_context(context))

    # Summary instructions
    instructions = _load_summary_instructions()
    if instructions:
        sections.append("\n=== SUMMARY INSTRUCTIONS ===")
        sections.append(instructions)

    # Cache emails and return file paths
    paths = ensure_cached(service, message_ids)
    sections.append(f"\n=== EMAIL FILES ({len(paths)} emails) ===")
    sections.append("Read each file below to get the email content:")
    for path in paths:
        sections.append(str(path.resolve()))

    return "\n".join(sections)
