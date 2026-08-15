from dataclasses import dataclass
from enum import StrEnum


class SkillMatchType(StrEnum):
    EXACT = "exact"
    ALIAS = "alias"
    UNMATCHED = "unmatched"


@dataclass(frozen=True, slots=True)
class SkillNormalizationResult:
    raw_text: str
    canonical_key: str | None
    canonical_name: str | None
    match_type: SkillMatchType
    taxonomy_version: str
