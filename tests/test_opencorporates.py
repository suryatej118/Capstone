from backend.enrichment.opencorporates import _normalize_company_name


def test_normalize_removes_corporate_suffix():
    assert _normalize_company_name("MICROSOFT CORPORATION") == "microsoft"


def test_normalize_handles_limited_company():
    assert _normalize_company_name("Acme Technologies Ltd.") == "acme technologies"


def test_normalize_handles_llc():
    assert _normalize_company_name("Example Technologies LLC") == "example technologies"


def test_normalize_handles_punctuation():
    assert _normalize_company_name("A.B.C. Pvt. Ltd.") == "a b c"