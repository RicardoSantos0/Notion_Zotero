"""Base types for extraction templates."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class ColumnDefinition:
    name: str
    aliases: List[str] = field(default_factory=list)
    required: bool = False

    def matches(self, header: str) -> bool:
        if not header:
            return False
        h = header.strip().lower()
        if h == self.name.lower():
            return True
        for a in self.aliases:
            if a.lower() == h:
                return True
        return False


@dataclass
class ExtractionTemplate:
    template_id: str
    display_name: str
    expected_columns: List[ColumnDefinition] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def validate_extraction_row(self, row: dict) -> List[str]:
        """Validate a single extracted row against the expected columns.

        Returns a list of error strings (empty list means the row is valid).
        A required column is considered missing only when neither its canonical
        name nor any of its aliases appear as a key in *row*.
        """
        errors: List[str] = []
        for col in self.expected_columns:
            if col.required and col.name not in row:
                alias_found = any(alias in row for alias in (col.aliases or []))
                if not alias_found:
                    errors.append(f"Missing required column: {col.name!r}")
        return errors


@dataclass
class TemplateMatchRule:
    required_headers: List[str] = field(default_factory=list)
    min_matches: int = 1

    def matches(self, headers: List[str]) -> bool:
        if not headers:
            return False
        count = 0
        low = [h.lower() for h in headers]
        for req in self.required_headers:
            if req.lower() in " ".join(low):
                count += 1
        return count >= self.min_matches


__all__ = ["ColumnDefinition", "ExtractionTemplate", "TemplateMatchRule"]
