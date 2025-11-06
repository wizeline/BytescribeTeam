import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.app.main import app
from api.app.routers.beckrock import router

client = TestClient(app)

@pytest.fixture
def mock_bedrock_client():
    with patch('api.app.routers.beckrock.boto3.client') as mock_client:
        yield mock_client

def test_generate_text(mock_bedrock_client):
    mock_response = {
        'body': b'{"completion":"Generated text"}'
    }
    mock_bedrock_client.return_value.invoke_model.return_value = mock_response

    response = client.post(
        '/generate',
        json={
            'prompt': 'Test prompt',
            'max_tokens': 100,
            'temperature': 0.7
        }
    )

    assert response.status_code == 200
    assert 'text' in response.json()

def test_invalid_request():
    response = client.post(
        '/generate',
        json={
            'prompt': '',  # Invalid empty prompt
            'max_tokens': 100,
            'temperature': 0.7
        }
    )
    assert response.status_code == 422

def test_bedrock_error(mock_bedrock_client):
    mock_bedrock_client.return_value.invoke_model.side_effect = Exception('AWS Error')
    
    response = client.post(
        '/generate',
        json={
            'prompt': 'Test prompt',
            'max_tokens': 100,
            'temperature': 0.7
        }
    )
    
    assert response.status_code == 500
    assert 'error' in response.json()
