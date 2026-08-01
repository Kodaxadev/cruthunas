from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AdoptionGap:
    code: str
    category: str
    message: str
    path: str
    automatic: bool
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdoptionReport:
    root: str
    gaps: tuple[AdoptionGap, ...]

    @property
    def ok(self) -> bool:
        return not self.gaps

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": self.root,
            "summary": {
                "gaps": len(self.gaps),
                "automatic": sum(item.automatic for item in self.gaps),
                "manual": sum(not item.automatic for item in self.gaps),
            },
            "gaps": [item.to_dict() for item in self.gaps],
        }
