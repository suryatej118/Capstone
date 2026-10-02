from backend.enrichment.company import extract_company_name


def test_extract_company_from_hiring_statement():
    text = "Acme Technologies is hiring Java developers."

    assert extract_company_name(text) == "Acme Technologies"


def test_extract_company_from_join_statement():
    text = "Join Microsoft as a Software Engineer."

    assert extract_company_name(text) == "Microsoft"


def test_extract_company_from_hiring_at_statement():
    text = "We are hiring at Google for backend engineers."

    assert extract_company_name(text) == "Google"


def test_extract_company_returns_none_when_not_found():
    text = "We are looking for talented software engineers."

    assert extract_company_name(text) is None


def test_extract_company_handles_empty_text():
    assert extract_company_name("") is None