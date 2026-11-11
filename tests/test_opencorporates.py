
from backend.enrichment.opencorporates import match_company_name


def test_exact_company_name_match(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.opencorporates.search_company",
        lambda name: {
            "results": {
                "companies": [
                    {
                        "company": {
                            "name": "Example Technologies Private Limited",
                            "company_number": "123456",
                            "jurisdiction_code": "in",
                            "current_status": "Active",
                            "opencorporates_url": "https://example.com",
                        }
                    }
                ]
            }
        },
    )

    result = match_company_name(
        "Example Technologies Private Limited"
    )

    assert result["matched"] is True
    assert result["match_type"] == "exact"
    assert result["similarity"] == 1.0
    assert result["company"]["current_status"] == "Active"


def test_fuzzy_company_name_match(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.opencorporates.search_company",
        lambda name: {
            "results": {
                "companies": [
                    {
                        "company": {
                            "name": "Example Technology Limited",
                            "company_number": "123456",
                            "jurisdiction_code": "in",
                            "current_status": "Active",
                        }
                    }
                ]
            }
        },
    )

    result = match_company_name(
        "Example Technologies Limited"
    )

    assert result["matched"] is True
    assert result["match_type"] == "fuzzy"
    assert result["company"] is not None


def test_no_company_match(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.opencorporates.search_company",
        lambda name: {"results": {"companies": []}},
    )

    result = match_company_name("Unknown Company")

    assert result["matched"] is False
    assert result["match_type"] == "no_match"
    assert result["company"] is None
    assert result["candidates"] == []


def test_below_threshold_match(monkeypatch):
    monkeypatch.setattr(
        "backend.enrichment.opencorporates.search_company",
        lambda name: {
            "results": {
                "companies": [
                    {
                        "company": {
                            "name": "Completely Different Corporation",
                            "company_number": "123456",
                            "jurisdiction_code": "in",
                            "current_status": "Active",
                        }
                    }
                ]
            }
        },
    )

    result = match_company_name("Example Technologies")

    assert result["matched"] is False
    assert result["match_type"] == "below_threshold"


def test_invalid_company_name():
    result = match_company_name("   ")

    assert result["matched"] is False
    assert result["match_type"] == "invalid_input"
