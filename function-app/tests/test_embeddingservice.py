from unittest.mock import Mock, MagicMock, create_autospec
import pytest
from src.embeddingservice import EmbeddingService
from openai import AzureOpenAI

@pytest.fixture
def mock_openai_client():
    client = create_autospec(AzureOpenAI, instance=True)

    mock_embeddings_api = MagicMock()

    mock_embedding_data = [0.1] * 1536
    mock_create_response = Mock(data=[Mock(embedding=mock_embedding_data)])
    mock_embeddings_api.create.return_value = mock_create_response

    client.embeddings = mock_embeddings_api

    return client

def test_get_embedding_happy_path(mock_openai_client):
    service = EmbeddingService(mock_openai_client)
    test_text = "sample query"

    result = service.get_embedding(test_text)

    mock_openai_client.embeddings.create.assert_called_once_with(
        input=[test_text],
        model="text-embedding-ada-002"
    )

    assert result == [0.1] * 1536
    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(x, float) for x in result)