import pytest
from pydantic import ValidationError
from api.app.models.bedrock import BedrockRequest

def test_valid_bedrock_request():
    request_data = {
        'prompt': 'Test prompt',
        'max_tokens': 100,
        'temperature': 0.7
    }
    request = BedrockRequest(**request_data)
    assert request.prompt == 'Test prompt'
    assert request.max_tokens == 100
    assert request.temperature == 0.7

def test_invalid_temperature():
    with pytest.raises(ValidationError):
        BedrockRequest(
            prompt='Test',
            max_tokens=100,
            temperature=2.0  # Invalid temperature
        )

def test_missing_required_fields():
    with pytest.raises(ValidationError):
        BedrockRequest()

def test_max_tokens_validation():
    with pytest.raises(ValidationError):
        BedrockRequest(
            prompt='Test',
            max_tokens=-1,  # Invalid tokens
            temperature=0.5
        )
