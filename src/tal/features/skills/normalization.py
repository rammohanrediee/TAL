from dataclasses import dataclass

from tal.features.skills.models import (
    SkillMatchType,
    SkillNormalizationResult,
)


@dataclass(frozen=True, slots=True)
class SkillTaxonomyEntry:
    key: str
    name: str
    aliases: tuple[str, ...]
    category: str


def _comparison_token(value: str) -> str:
    return " ".join(value.casefold().split())


class SkillNormalizer:
    def __init__(
        self,
        *,
        taxonomy_version: str,
        entries: tuple[SkillTaxonomyEntry, ...],
    ) -> None:
        self.taxonomy_version = taxonomy_version
        self.entries = entries

    def normalize(self, raw_text: str) -> SkillNormalizationResult:
        token = _comparison_token(raw_text)

        for entry in self.entries:
            canonical_tokens = {
                _comparison_token(entry.key),
                _comparison_token(entry.name),
            }

            if token in canonical_tokens:
                return self._matched_result(
                    raw_text=raw_text,
                    entry=entry,
                    match_type=SkillMatchType.EXACT,
                )

        for entry in self.entries:
            alias_tokens = {_comparison_token(alias) for alias in entry.aliases}

            if token in alias_tokens:
                return self._matched_result(
                    raw_text=raw_text,
                    entry=entry,
                    match_type=SkillMatchType.ALIAS,
                )

        return SkillNormalizationResult(
            raw_text=raw_text,
            canonical_key=None,
            canonical_name=None,
            match_type=SkillMatchType.UNMATCHED,
            taxonomy_version=self.taxonomy_version,
        )

    def _matched_result(
        self,
        *,
        raw_text: str,
        entry: SkillTaxonomyEntry,
        match_type: SkillMatchType,
    ) -> SkillNormalizationResult:
        return SkillNormalizationResult(
            raw_text=raw_text,
            canonical_key=entry.key,
            canonical_name=entry.name,
            match_type=match_type,
            taxonomy_version=self.taxonomy_version,
        )
