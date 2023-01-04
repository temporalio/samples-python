import pytest
from fastapi.testclient import TestClient
from temporalio.client import Client

from fast_api.run_fast import app

client = TestClient(app)


class ServerAddress:
    def get_address(self) -> str:
        raise NotImplementedError


class RealServerAddress(ServerAddress):
    def get_address(self) -> str:
        return "localhost:7233"


class MockServerAddress(ServerAddress):
    def get_address(self) -> str:
        return "mock_server:1234"


@pytest.fixture
def server_address():
    return MockServerAddress()


def test_read_main(server_address):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Hello, World!"
