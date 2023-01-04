import pytest
from flask.testing import FlaskClient

from flask_api.run_flask import app


@pytest.fixture
def flask_client():
    with app.test_client() as client:
        yield client


def test_main(flask_client: FlaskClient):
    response = flask_client.get("/")
    assert response.status_code == 200
    assert b"Hello, World!" in response.data
