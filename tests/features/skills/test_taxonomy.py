from tal.features.matching.fit import _mentions_skill, taxonomy_terms_in_text
from tal.features.skills.taxonomy import SKILLS_V1_ENTRIES, SKILLS_V1_NORMALIZER


def test_skills_v1_taxonomy_has_expanded_coverage() -> None:
    keys = {entry.key for entry in SKILLS_V1_ENTRIES}
    assert "kubernetes" in keys
    assert "javascript" in keys
    assert "salesforce" in keys
    assert "embedded_systems" in keys
    assert "ux_design" in keys
    assert "penetration_testing" in keys
    assert len(SKILLS_V1_ENTRIES) >= 90


def test_java_does_not_match_javascript_in_job_text() -> None:
    jd = "We need strong JavaScript experience for our frontend team."
    assert not _mentions_skill("Java", jd)
    assert "JavaScript" in taxonomy_terms_in_text(jd)


def test_skills_v1_normalizer_maps_common_aliases() -> None:
    assert SKILLS_V1_NORMALIZER.normalize("k8s").canonical_key == "kubernetes"
    assert SKILLS_V1_NORMALIZER.normalize("Golang").canonical_key == "go"
    assert SKILLS_V1_NORMALIZER.normalize("JS").canonical_key == "javascript"
    assert SKILLS_V1_NORMALIZER.normalize("SFDC").canonical_key == "salesforce"
    assert SKILLS_V1_NORMALIZER.normalize("FreeRTOS").canonical_key == "freertos"
    assert SKILLS_V1_NORMALIZER.normalize("AppSec").canonical_key == "application_security"


def test_taxonomy_detects_security_and_design_terms_in_jd() -> None:
    security_jd = "Experience with OWASP, SIEM, and Splunk for enterprise security."
    design_jd = "Strong Figma, wireframing, and WCAG accessibility skills required."
    assert "OWASP" in taxonomy_terms_in_text(security_jd)
    assert "Splunk" in taxonomy_terms_in_text(security_jd)
    assert "Figma" in taxonomy_terms_in_text(design_jd)
    assert "Wireframing" in taxonomy_terms_in_text(design_jd)
    assert "Accessibility" in taxonomy_terms_in_text(design_jd)