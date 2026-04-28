import pprint

from notion_zotero.analysis.table_normalization import extract_canonical_terms
from notion_zotero.schemas.domain_packs import education_learning_analytics as ela


def test_alias_mappings():
    tokens_expected = {
        "Pre-Test": "Learning Gains",
        "5. Job Alternative/ Career": "Professional background records",
        "6. Personal/ Family Aspects": "Student demographics/characteristics",
        "Course Information": "Course/content metadata",
        "chapter summaries": "Course/content metadata",
    }

    for token, canonical in tokens_expected.items():
        recs = extract_canonical_terms(token, alias_patterns=ela.DATA_SOURCE_ALIAS_PATTERNS, keep_unmatched=True)
        # ensure at least one matched record with expected canonical value
        assert any(r["value"] == canonical and r["matched"] for r in recs), f"{token} did not map to {canonical}: {pprint.pformat(recs)}"