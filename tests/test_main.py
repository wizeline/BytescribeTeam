import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'message': 'Welcome to the API'}

def test_health_check():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'healthy'}

def test_cors_headers():
    response = client.options('/')
    assert response.headers['access-control-allow-origin'] == '*'

@pytest.mark.asyncio
async def test_startup_event():
    # Test startup event handlers
    pass

@pytest.mark.asyncio
async def test_shutdown_event():
    # Test shutdown event handlers
    pass
