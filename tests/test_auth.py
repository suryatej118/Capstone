from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


def test_protected_endpoint_requires_a_bearer_token():
    main.app.dependency_overrides.clear()

    response = client.get("/dashboard/stats")

    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected(monkeypatch):
    main.app.dependency_overrides.clear()
    monkeypatch.setattr("backend.auth.get_firebase_app", lambda: object())
    monkeypatch.setattr(
        "backend.auth.firebase_auth.verify_id_token",
        lambda token: (_ for _ in ()).throw(ValueError("invalid token")),
    )

    response = client.get(
        "/dashboard/stats",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_authenticated_test_user_can_access_dashboard():
    response = client.get("/dashboard/stats")

    assert response.status_code == 200
    assert response.json()["total_scans"] >= 0


def test_scan_history_isolated_between_authenticated_users(monkeypatch):
    monkeypatch.setattr(main, "analyze_rules", lambda text: (0, []))
    monkeypatch.setattr(main, "predict_scam_probability", lambda text: 0.1)
    monkeypatch.setattr(main, "extract_emails", lambda text: [])
    monkeypatch.setattr(main, "extract_domains", lambda text: [])
    monkeypatch.setattr(main, "extract_company_name", lambda text: None)
    monkeypatch.setattr(
        main,
        "detect_careers_page",
        lambda text, domain: {"present": False, "url": None, "method": "none"},
    )
    monkeypatch.setattr(main, "match_company_name", lambda name: {"matched": False})

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "user-a",
        "email": "a@example.com",
    }
    response = client.post(
        "/analyze",
        json={"text": "A private scan belonging to user A.", "save_report": True},
    )
    assert response.status_code == 200
    scan_id = response.json()["scan_id"]

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "user-b",
        "email": "b@example.com",
    }
    history = client.get("/scans")
    assert history.status_code == 200
    assert history.json()["total"] == 0

    detail = client.get(f"/scans/{scan_id}")
    assert detail.status_code == 404
