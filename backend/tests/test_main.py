from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_returns_api_message():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Online Shop API"}


def test_unknown_page_returns_not_found():
    response = client.get("/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
