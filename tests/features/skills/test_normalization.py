from tal.features.skills.models import SkillMatchType
from tal.features.skills.normalization import (
    SkillNormalizer,
    SkillTaxonomyEntry,
)
from tal.features.skills.taxonomy import SKILLS_V1_NORMALIZER


def test_normalize_skill_resolves_alias_with_taxonomy_version() -> None:
    # Arrange
    normalizer = SkillNormalizer(
        taxonomy_version="skills-v1",
        entries=(
            SkillTaxonomyEntry(
                key="fastapi",
                name="FastAPI",
                aliases=("fast api",),
                category="framework",
            ),
        ),
    )

    # Act
    result = normalizer.normalize(" Fast API ")

    # Assert
    assert result.canonical_key == "fastapi"
    assert result.canonical_name == "FastAPI"
    assert result.match_type is SkillMatchType.ALIAS
    assert result.taxonomy_version == "skills-v1"


def test_normalize_skill_preserves_unmatched_input() -> None:
    # Arrange
    normalizer = SkillNormalizer(
        taxonomy_version="skills-v1",
        entries=(),
    )

    # Act
    result = normalizer.normalize(" Quantum Networking ")

    # Assert
    assert result.raw_text == " Quantum Networking "
    assert result.canonical_key is None
    assert result.canonical_name is None
    assert result.match_type is SkillMatchType.UNMATCHED
    assert result.taxonomy_version == "skills-v1"


def test_skills_v1_taxonomy_normalizes_postgres_alias() -> None:
    # Arrange
    raw_skill = " Postgres "

    # Act
    result = SKILLS_V1_NORMALIZER.normalize(raw_skill)

    # Assert
    assert result.raw_text == raw_skill
    assert result.canonical_key == "postgresql"
    assert result.canonical_name == "PostgreSQL"
    assert result.match_type is SkillMatchType.ALIAS
    assert result.taxonomy_version == "skills-v1"
