import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_bedrock_client():
    with patch('api.app.routers.beckrock.boto3.client') as mock_client:
        yield mock_client

def test_invoke_model_success(client, mock_bedrock_client):
    mock_response = {
        'body': b'{"completion": "Test response"}'
    }
    mock_bedrock_client.return_value.invoke_model.return_value = mock_response

    response = client.post('/bedrock/invoke', json={
        'prompt': 'Test prompt',
        'max_tokens': 100,
        'temperature': 0.7
    })

    assert response.status_code == 200
    assert 'completion' in response.json()

def test_invoke_model_error(client, mock_bedrock_client):
    mock_bedrock_client.return_value.invoke_model.side_effect = Exception('API Error')

    response = client.post('/bedrock/invoke', json={
        'prompt': 'Test prompt',
        'max_tokens': 100,
        'temperature': 0.7
    })

    assert response.status_code == 500

def test_invalid_request_body(client):
    response = client.post('/bedrock/invoke', json={})
    assert response.status_code == 422

def test_invalid_content_type(client):
    response = client.post('/bedrock/invoke', data='not json')
    assert response.status_code == 422