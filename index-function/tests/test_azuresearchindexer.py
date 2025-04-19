import json
import logging
import pytest
import requests 
from unittest.mock import ANY 

from src.azuresearchindexer import AzureSearchIndexer

# --- Test Data ---

TEST_SEARCH_URL = "https://fake-search-service.search.windows.net"
TEST_SEARCH_KEY = "dummy-api-key"
TEST_INDEX_NAME = AzureSearchIndexer.INDEX_NAME 
TEST_API_VERSION = AzureSearchIndexer.API_VERSION

EXPECTED_POST_URL = AzureSearchIndexer.SEARCH_API_ULR.format(
    TEST_SEARCH_URL, TEST_INDEX_NAME, TEST_API_VERSION
)

# --- Fixtures ---

@pytest.fixture
def indexer():
    """Provides an instance of AzureSearchIndexer with test credentials."""
    return AzureSearchIndexer(
        search_api_url=TEST_SEARCH_URL,
        search_api_key=TEST_SEARCH_KEY
    )

# --- Test Class ---

class TestAzureSearchIndexer:

    def test_index_document_happy_path_dict_metadata(self, indexer, requests_mock):
        # Arrange
        input_chunk = {
            "id": "test-id-1",
            "content": "This is the chunk content.",
            "metadata": {
                "source_page": 5,
                "chunk_index": 2
            }
        }
        input_embedding = [0.1, 0.2, 0.3, 0.4]

        # Expected payload after modifications by the method
        expected_payload_value = {
            "id": "test-id-1",
            "content": "This is the chunk content.",
            "metadata": json.dumps({"source_page": 5, "chunk_index": 2}), # Stringified
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "@search.action": "upload"
        }
        expected_post_data = {"value": [expected_payload_value]}

        # Mock the specific POST request
        requests_mock.post(
            EXPECTED_POST_URL,
            status_code=200, # Simulate success
            json={"value": [{"key": "test-id-1", "status": True, "errorMessage": None, "statusCode": 200}]}
        )

        # Act
        # Pass a copy if you want to ensure the original input_chunk isn't modified
        # (though this method seems to modify it in place)
        indexer.index_document(input_chunk, input_embedding)

        # Assert
        assert requests_mock.called_once
        history = requests_mock.request_history
        assert history[0].url == EXPECTED_POST_URL
        assert history[0].method == "POST"
        assert history[0].headers["api-key"] == TEST_SEARCH_KEY
        assert history[0].headers["Content-Type"] == "application/json"
        # Compare the actual JSON sent in the request body
        assert json.loads(history[0].text) == expected_post_data

    def test_index_document_metadata_not_dict(self, indexer, requests_mock):
        # Arrange
        input_chunk = {
            "id": "test-id-2",
            "content": "Another chunk.",
            "metadata": "some_string_metadata" # Metadata is NOT a dict
        }
        input_embedding = [0.5, 0.6]

        # Expected payload - metadata should NOT be json.dumps'd
        expected_payload_value = {
            "id": "test-id-2",
            "content": "Another chunk.",
            "metadata": "some_string_metadata", # Kept as is
            "embedding": [0.5, 0.6],
            "@search.action": "upload"
        }
        expected_post_data = {"value": [expected_payload_value]}

        requests_mock.post(EXPECTED_POST_URL, status_code=201) # Simulate 201 Created

        # Act
        indexer.index_document(input_chunk, input_embedding)

        # Assert
        assert requests_mock.called_once
        history = requests_mock.request_history
        assert history[0].url == EXPECTED_POST_URL
        assert json.loads(history[0].text) == expected_post_data
        assert history[0].headers["api-key"] == TEST_SEARCH_KEY

    def test_index_document_handles_api_error(self, indexer, requests_mock, caplog):
        # Arrange
        input_chunk = {"id": "test-id-3", "content": "Error case."}
        input_embedding = [0.7]

        # Expected payload structure (even on error, we expect it to be sent)
        expected_payload_value = {
            "id": "test-id-3",
            "content": "Error case.",
            # No metadata key in input, so shouldn't be in output before sending
            "embedding": [0.7],
            "@search.action": "upload"
        }
        expected_post_data = {"value": [expected_payload_value]}

        # Simulate an API error (e.g., Bad Request)
        error_response_text = '{"error": {"code": "InvalidRequest", "message": "Something went wrong"}}'
        requests_mock.post(
            EXPECTED_POST_URL,
            status_code=400,
            text=error_response_text
        )

        # Act
        # Use caplog to capture logging output
        with caplog.at_level(logging.INFO):
            indexer.index_document(input_chunk, input_embedding)

        # Assert
        assert requests_mock.called_once
        history = requests_mock.request_history
        assert json.loads(history[0].text) == expected_post_data # Verify payload was still sent correctly

        # Assert that the error status code and response text were logged
        assert f"Status Code: 400" in caplog.text
        assert f"Response: {error_response_text}" in caplog.text

