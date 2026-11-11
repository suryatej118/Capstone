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


def test_extract_company_from_inviting_applications():
    text = (
        "ABC Technologies is inviting applications "
        "for Software Engineer Intern positions."
    )

    assert extract_company_name(text) == "ABC Technologies"


def test_extract_company_from_recruitment_announcement():
    text = (
        "Global Tech Solutions Pvt. Ltd. announces "
        "recruitment for freshers."
    )

    assert extract_company_name(text) == "Global Tech Solutions Pvt. Ltd"


def test_extract_company_from_expanding_team():
    text = "Google is expanding its team."

    assert extract_company_name(text) == "Google"
