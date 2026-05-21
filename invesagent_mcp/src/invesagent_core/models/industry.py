from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class IndustryMember:
    """One instrument in an industry pool."""

    symbol: str
    name: str | None = None
    industry: str | None = None
    area: str | None = None
    market: str | None = None
    list_date: str | None = None
    provider: str | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class IndustryMembersResult:
    """Unified result for an industry member query."""

    success: bool
    industry: str
    provider: str
    market: str
    members: list[IndustryMember] = field(default_factory=list)
    matched_industries: list[str] = field(default_factory=list)
    error_type: str | None = None
    message: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["members"] = [member.to_dict() for member in self.members]
        return data

