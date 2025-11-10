import pytest
from fastapi.testclient import TestClient
from api.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_read_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'message': 'Welcome to the API'}

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'healthy'}

def test_cors_headers(client):
    response = client.options('/')
    assert response.headers['access-control-allow-origin'] == '*'

def test_invalid_route(client):
    response = client.get('/invalid')
    assert response.status_code == 404