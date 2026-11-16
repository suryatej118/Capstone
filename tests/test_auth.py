from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

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


def test_expired_bearer_token_is_rejected(monkeypatch):
    main.app.dependency_overrides.clear()
    monkeypatch.setattr("backend.auth.get_firebase_app", lambda: object())
    monkeypatch.setattr(
        "backend.auth.firebase_auth.verify_id_token",
        lambda token: (_ for _ in ()).throw(
            firebase_auth.ExpiredIdTokenError("expired token", None)
        ),
    )

    response = client.get(
        "/dashboard/stats",
        headers={"Authorization": "Bearer expired-token"},
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
        "uid": "isolation-user-a",
        "email": "isolation-a@example.com",
    }
    response = client.post(
        "/analyze",
        json={"text": "A private scan belonging to user A.", "save_report": True},
    )
    assert response.status_code == 200
    scan_id = response.json()["scan_id"]

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "isolation-user-b",
        "email": "isolation-b@example.com",
    }
    history = client.get("/scans")
    assert history.status_code == 200
    assert history.json()["total"] == 0

    detail = client.get(f"/scans/{scan_id}")
    assert detail.status_code == 404


def test_dashboard_stats_are_isolated_between_two_users(monkeypatch):
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
        "uid": "dashboard-user-a",
        "email": "dashboard-a@example.com",
    }
    assert client.post(
        "/analyze",
        json={"text": "A dashboard scan belonging to user A.", "save_report": True},
    ).status_code == 200

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "dashboard-user-b",
        "email": "dashboard-b@example.com",
    }
    assert client.post(
        "/analyze",
        json={"text": "A dashboard scan belonging to user B.", "save_report": True},
    ).status_code == 200

    user_b_stats = client.get("/dashboard/stats")
    assert user_b_stats.status_code == 200
    assert user_b_stats.json()["total_scans"] == 1

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "dashboard-user-a",
        "email": "dashboard-a@example.com",
    }
    user_a_stats = client.get("/dashboard/stats")
    assert user_a_stats.status_code == 200
    assert user_a_stats.json()["total_scans"] == 1


def test_scan_detail_enforces_ownership(monkeypatch):
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
        "uid": "ownership-user-a",
        "email": "ownership-a@example.com",
    }
    response = client.post(
        "/analyze",
        json={"text": "An ownership test scan for user A.", "save_report": True},
    )
    scan_id = response.json()["scan_id"]
    assert client.get(f"/scans/{scan_id}").status_code == 200

    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "uid": "ownership-user-b",
        "email": "ownership-b@example.com",
    }
    assert client.get(f"/scans/{scan_id}").status_code == 404
