from fastapi.testclient import TestClient

from fast_api.run_fast import app

def test_main():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == "Hello, World!"
