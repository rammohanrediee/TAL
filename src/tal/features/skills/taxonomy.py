from tal.features.skills.normalization import (
    SkillNormalizer,
    SkillTaxonomyEntry,
)

SKILLS_V1_VERSION = "skills-v1"

SKILLS_V1_ENTRIES: tuple[SkillTaxonomyEntry, ...] = (
    SkillTaxonomyEntry(
        key="python",
        name="Python",
        aliases=("python3",),
        category="language",
    ),
    SkillTaxonomyEntry(
        key="fastapi",
        name="FastAPI",
        aliases=("fast api",),
        category="framework",
    ),
    SkillTaxonomyEntry(
        key="postgresql",
        name="PostgreSQL",
        aliases=("postgres", "postgres sql"),
        category="database",
    ),
    SkillTaxonomyEntry(
        key="react",
        name="React",
        aliases=("react.js",),
        category="framework",
    ),
    SkillTaxonomyEntry(
        key="typescript",
        name="TypeScript",
        aliases=("typescript language", "ts"),
        category="language",
    ),
)

SKILLS_V1_NORMALIZER = SkillNormalizer(
    taxonomy_version=SKILLS_V1_VERSION,
    entries=SKILLS_V1_ENTRIES,
)
