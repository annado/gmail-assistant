"""Load personal context from context.toml for school email summarization."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ChildContext:
    name: str
    grade: int | str = ""
    level: str = ""
    school: str = ""
    school_domain: str = ""
    division: str = ""
    sports: tuple[str, ...] = ()
    activities: tuple[str, ...] = ()
    teachers: tuple[str, ...] = ()


@dataclass(frozen=True)
class PersonalContext:
    children: tuple[ChildContext, ...] = ()


def _parse_child(child_data: dict) -> ChildContext | None:
    """Parse a single child dict from TOML into a ChildContext."""
    if not isinstance(child_data, dict) or not child_data.get("name"):
        return None

    return ChildContext(
        name=child_data.get("name", ""),
        grade=child_data.get("grade", ""),
        level=child_data.get("level", ""),
        school=child_data.get("school", ""),
        school_domain=child_data.get("school_domain", ""),
        division=child_data.get("division", ""),
        sports=tuple(child_data.get("sports", [])),
        activities=tuple(child_data.get("activities", [])),
        teachers=tuple(child_data.get("teachers", [])),
    )


def load_context(path: str | Path = "context.toml") -> PersonalContext:
    """Load personal context from a TOML file.

    Returns PersonalContext(children=()) if the file is absent or malformed.
    Supports both [[children]] array and singular [child] table.
    """
    path = Path(path)
    if not path.exists():
        return PersonalContext()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return PersonalContext()

    parsed: list[ChildContext] = []

    # Support [[children]] array of tables
    for child_data in data.get("children", []):
        child = _parse_child(child_data)
        if child:
            parsed.append(child)

    # Also support singular [child] for backwards compatibility
    if not parsed:
        child_data = data.get("child")
        if child_data:
            child = _parse_child(child_data)
            if child:
                parsed.append(child)

    return PersonalContext(children=tuple(parsed))
