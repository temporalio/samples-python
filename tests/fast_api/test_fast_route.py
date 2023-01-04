from fastapi.testclient import TestClient

from fast_api.run_fast import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Hello, World!"
