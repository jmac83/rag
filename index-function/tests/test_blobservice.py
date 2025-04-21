import logging
import pytest
from unittest.mock import MagicMock, patch, call  
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.storage.blob import BlobProperties 

from blob_service import BlobStorageService


# Fixture to create a mock BlobServiceClient
@pytest.fixture
def mock_blob_service_client(mocker):
    """Provides a mocked BlobServiceClient instance."""
    return mocker.MagicMock()


# Fixture to create an instance of the service with the mocked client
@pytest.fixture
def blob_storage_service(mock_blob_service_client):
    """Provides an instance of BlobStorageService with a mocked client."""
    return BlobStorageService(mock_blob_service_client)


# --- Tests for list_blob_names ---


def test_list_blob_names_success(
    blob_storage_service, mock_blob_service_client, mocker
):
    """Test listing blobs successfully."""
    container_name = "test-container"
    mock_container_client = mocker.MagicMock()
    mock_blob_service_client.get_container_client.return_value = (
        mock_container_client
    )

    # Create mock BlobProperties objects
    mock_blob1 = mocker.MagicMock(spec=BlobProperties)
    mock_blob1.name = "folder/blob1.txt"
    mock_blob2 = mocker.MagicMock(spec=BlobProperties)
    mock_blob2.name = "blob2.jpg"

    mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]

    result = blob_storage_service.list_blob_names(container_name)

    expected_result = {
        "blobs": [
            {"name": f"{container_name}/folder/blob1.txt"},
            {"name": f"{container_name}/blob2.jpg"},
        ]
    }
    assert result == expected_result
    mock_blob_service_client.get_container_client.assert_called_once_with(
        container_name
    )
    mock_container_client.list_blobs.assert_called_once_with(
        name_starts_with=None
    )


def test_list_blob_names_with_prefix(
    blob_storage_service, mock_blob_service_client, mocker
):
    """Test listing blobs successfully with a prefix."""
    container_name = "test-container"
    prefix = "folder/"
    mock_container_client = mocker.MagicMock()
    mock_blob_service_client.get_container_client.return_value = (
        mock_container_client
    )

    mock_blob1 = mocker.MagicMock(spec=BlobProperties)
    mock_blob1.name = "folder/blob1.txt"
    mock_container_client.list_blobs.return_value = [mock_blob1]

    result = blob_storage_service.list_blob_names(container_name, prefix=prefix)

    expected_result = {
        "blobs": [{"name": f"{container_name}/folder/blob1.txt"}]
    }
    assert result == expected_result
    mock_blob_service_client.get_container_client.assert_called_once_with(
        container_name
    )
    mock_container_client.list_blobs.assert_called_once_with(
        name_starts_with=prefix
    )


def test_list_blob_names_container_not_found(
    blob_storage_service, mock_blob_service_client, caplog
):
    """Test listing blobs when the container doesn't exist."""
    container_name = "nonexistent-container"
    mock_blob_service_client.get_container_client.side_effect = (
        ResourceNotFoundError("Container not found")
    )

    with caplog.at_level(logging.WARNING):
        result = blob_storage_service.list_blob_names(container_name)

    assert result == {"blobs": []}
    assert f"Container not found: {container_name}" in caplog.text
    mock_blob_service_client.get_container_client.assert_called_once_with(
        container_name
    )


def test_list_blob_names_other_exception(
    blob_storage_service, mock_blob_service_client, mocker, caplog
):
    """Test listing blobs when an unexpected error occurs."""
    container_name = "error-container"
    mock_container_client = mocker.MagicMock()
    mock_blob_service_client.get_container_client.return_value = (
        mock_container_client
    )
    mock_container_client.list_blobs.side_effect = Exception("Unexpected error")

    with pytest.raises(Exception, match="Unexpected error"), caplog.at_level(
        logging.ERROR
    ):
        blob_storage_service.list_blob_names(container_name)

    assert (
        f"Error listing blob names in {container_name}: Unexpected error"
        in caplog.text
    )
    mock_blob_service_client.get_container_client.assert_called_once_with(
        container_name
    )
    mock_container_client.list_blobs.assert_called_once_with(
        name_starts_with=None
    )


# --- Tests for upload_blob ---


def test_upload_blob_success_overwrite_true(
    blob_storage_service, mock_blob_service_client, mocker, caplog
):
    """Test successful blob upload with overwrite=True."""
    container_name = "upload-container"
    blob_name = "new_file.txt"
    file_content = b"this is test content"
    full_path = f"{container_name}/{blob_name}"
    mock_blob_client = mocker.MagicMock()
    mock_blob_client.url = f"http://mockstorage/{container_name}/{blob_name}"
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client

    with caplog.at_level(logging.INFO):
        result = blob_storage_service.upload_blob(
            container_name, blob_name, file_content, overwrite=True
        )

    expected_result = {
        "success": True,
        "path": full_path,
        "url": mock_blob_client.url,
    }
    assert result == expected_result
    mock_blob_service_client.get_blob_client.assert_called_once_with(
        container=container_name, blob=blob_name
    )
    # Use call helper for checking arguments including keyword args
    mock_blob_client.upload_blob.assert_called_once_with(
        file_content, overwrite=True
    )
    assert f"Uploaded blob: {full_path}" in caplog.text


def test_upload_blob_success_overwrite_default(
    blob_storage_service, mock_blob_service_client, mocker, caplog
):
    """Test successful blob upload with default overwrite=True."""
    container_name = "upload-container"
    blob_name = "new_file_default.txt"
    file_content = b"more test content"
    full_path = f"{container_name}/{blob_name}"
    mock_blob_client = mocker.MagicMock()
    mock_blob_client.url = f"http://mockstorage/{container_name}/{blob_name}"
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client

    with caplog.at_level(logging.INFO):
        result = blob_storage_service.upload_blob(
            container_name, blob_name, file_content
        )  # Overwrite defaults to True

    expected_result = {
        "success": True,
        "path": full_path,
        "url": mock_blob_client.url,
    }
    assert result == expected_result
    mock_blob_service_client.get_blob_client.assert_called_once_with(
        container=container_name, blob=blob_name
    )
    mock_blob_client.upload_blob.assert_called_once_with(
        file_content, overwrite=True
    )  # Default is True
    assert f"Uploaded blob: {full_path}" in caplog.text


def test_upload_blob_exists_overwrite_false(
    blob_storage_service, mock_blob_service_client, mocker, caplog
):
    """Test upload failure when blob exists and overwrite=False."""
    container_name = "upload-container"
    blob_name = "existing_file.txt"
    file_content = b"this should not be uploaded"
    full_path = f"{container_name}/{blob_name}"
    mock_blob_client = mocker.MagicMock()
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client
    # Simulate ResourceExistsError when upload_blob is called
    mock_blob_client.upload_blob.side_effect = ResourceExistsError(
        "Blob already exists"
    )

    with caplog.at_level(logging.WARNING):
        result = blob_storage_service.upload_blob(
            container_name, blob_name, file_content, overwrite=False
        )

    expected_result = {
        "success": False,
        "error": "Blob already exists",
        "path": full_path,
    }
    assert result == expected_result
    mock_blob_service_client.get_blob_client.assert_called_once_with(
        container=container_name, blob=blob_name
    )
    mock_blob_client.upload_blob.assert_called_once_with(
        file_content, overwrite=False
    )
    assert f"Blob exists, overwrite=False: {full_path}" in caplog.text


def test_upload_blob_general_exception(
    blob_storage_service, mock_blob_service_client, mocker, caplog
):
    """Test upload failure due to an unexpected exception."""
    container_name = "upload-container"
    blob_name = "error_file.txt"
    file_content = b"this will fail"
    full_path = f"{container_name}/{blob_name}"
    mock_blob_client = mocker.MagicMock()
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client
    error_message = "Network connection failed"
    mock_blob_client.upload_blob.side_effect = Exception(error_message)

    with caplog.at_level(logging.ERROR):
        result = blob_storage_service.upload_blob(
            container_name, blob_name, file_content, overwrite=True
        )

    expected_result = {
        "success": False,
        "error": error_message,
        "path": full_path,
    }
    assert result == expected_result
    mock_blob_service_client.get_blob_client.assert_called_once_with(
        container=container_name, blob=blob_name
    )
    mock_blob_client.upload_blob.assert_called_once_with(
        file_content, overwrite=True
    )
    assert f"Failed to upload blob {full_path}: {error_message}" in caplog.text
