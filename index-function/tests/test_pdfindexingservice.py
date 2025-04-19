import io
import logging
from unittest.mock import MagicMock, call, patch
import pytest

from src.pdfprocessor import PDFProcessor
from src.embeddingservice import EmbeddingService
from src.azuresearchindexer import AzureSearchIndexer
from src.pdfindexingservice import PdfIndexingService

@pytest.fixture
def mock_pdf_processor():
    return MagicMock(spec=PDFProcessor)

@pytest.fixture
def mock_embedding_service():
    return MagicMock(spec=EmbeddingService)

@pytest.fixture
def mock_search_indexer():
    return MagicMock(spec=AzureSearchIndexer)

@pytest.fixture
def mock_logger():
    # Use autospec for better matching if Logger methods change
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def indexing_service(
    mock_pdf_processor,
    mock_embedding_service,
    mock_search_indexer,
    mock_logger
):
    return PdfIndexingService(
        pdf_processor=mock_pdf_processor,
        embedding_service=mock_embedding_service,
        search_indexer=mock_search_indexer,
        logger=mock_logger
    )

class TestPdfIndexingService:

    def test_process_and_index_pdf_happy_path(
        self,
        indexing_service,
        mock_pdf_processor,
        mock_embedding_service,
        mock_search_indexer,
        mock_logger
    ):
        dummy_stream = io.BytesIO(b"dummy pdf content")
        blob_name = "test.pdf"

        chunk1 = {"id": "uuid1", "content": "content one"}
        chunk2 = {"id": "uuid2", "content": "content two"}
        mock_pdf_processor.process_pdf_to_chunks.return_value = [chunk1, chunk2]

        embedding1 = [0.1, 0.2]
        embedding2 = [0.3, 0.4]
        mock_embedding_service.get_embedding.side_effect = [embedding1, embedding2]

        indexing_service.process_and_index_pdf(dummy_stream, blob_name)

        mock_pdf_processor.process_pdf_to_chunks.assert_called_once_with(dummy_stream)
        mock_logger.info.assert_any_call(f"Extracted 2 chunks from {blob_name}.")

        assert mock_embedding_service.get_embedding.call_count == 2
        mock_embedding_service.get_embedding.assert_has_calls([
            call("content one"),
            call("content two")
        ])

        assert mock_search_indexer.index_document.call_count == 2
        mock_search_indexer.index_document.assert_has_calls([
            call(chunk1, embedding1),
            call(chunk2, embedding2)
        ])
        mock_logger.info.assert_any_call(f"Successfully processed and initiated indexing for chunks from {blob_name}")

    def test_process_and_index_pdf_no_chunks(
        self,
        indexing_service,
        mock_pdf_processor,
        mock_embedding_service,
        mock_search_indexer,
        mock_logger
    ):
        dummy_stream = io.BytesIO(b"dummy pdf content")
        blob_name = "empty.pdf"

        mock_pdf_processor.process_pdf_to_chunks.return_value = []

        indexing_service.process_and_index_pdf(dummy_stream, blob_name)

        mock_pdf_processor.process_pdf_to_chunks.assert_called_once_with(dummy_stream)
        mock_logger.warning.assert_called_once_with(f"No text chunks were extracted from {blob_name}. Skipping indexing.")
        mock_embedding_service.get_embedding.assert_not_called()
        mock_search_indexer.index_document.assert_not_called()
        # Check the final success message is NOT logged
        assert call(f"Successfully processed and initiated indexing for chunks from {blob_name}") not in mock_logger.info.call_args_list


    def test_process_and_index_pdf_embedding_error_continues(
        self,
        indexing_service,
        mock_pdf_processor,
        mock_embedding_service,
        mock_search_indexer,
        mock_logger
    ):
        dummy_stream = io.BytesIO(b"dummy pdf content")
        blob_name = "error.pdf"
        test_exception = ValueError("Embedding failed")

        chunk1 = {"id": "uuid1", "content": "content one"}
        chunk2 = {"id": "uuid2", "content": "content two"} # This one will succeed
        mock_pdf_processor.process_pdf_to_chunks.return_value = [chunk1, chunk2]

        embedding2 = [0.3, 0.4]
        # First call fails, second succeeds
        mock_embedding_service.get_embedding.side_effect = [test_exception, embedding2]

        indexing_service.process_and_index_pdf(dummy_stream, blob_name)

        mock_pdf_processor.process_pdf_to_chunks.assert_called_once_with(dummy_stream)

        assert mock_embedding_service.get_embedding.call_count == 2
        mock_embedding_service.get_embedding.assert_has_calls([
            call("content one"),
            call("content two")
        ])

        # Indexing should only be called for the successful chunk (chunk2)
        mock_search_indexer.index_document.assert_called_once_with(chunk2, embedding2)

        # Check that the error for the specific chunk was logged
        mock_logger.error.assert_called_once_with(
            f"Error processing chunk uuid1 for {blob_name}: {test_exception}",
            exc_info=True
        )
        mock_logger.info.assert_any_call(f"Successfully processed and initiated indexing for chunks from {blob_name}")


    def test_process_and_index_pdf_indexing_error_continues(
        self,
        indexing_service,
        mock_pdf_processor,
        mock_embedding_service,
        mock_search_indexer,
        mock_logger
    ):
        dummy_stream = io.BytesIO(b"dummy pdf content")
        blob_name = "index_error.pdf"
        test_exception = ConnectionError("Search index unavailable")

        chunk1 = {"id": "uuid1", "content": "content one"} # This one fails indexing
        chunk2 = {"id": "uuid2", "content": "content two"} # This one succeeds
        mock_pdf_processor.process_pdf_to_chunks.return_value = [chunk1, chunk2]

        embedding1 = [0.1, 0.2]
        embedding2 = [0.3, 0.4]
        mock_embedding_service.get_embedding.side_effect = [embedding1, embedding2]

        # First call fails, second succeeds
        mock_search_indexer.index_document.side_effect = [test_exception, None]

        indexing_service.process_and_index_pdf(dummy_stream, blob_name)

        mock_pdf_processor.process_pdf_to_chunks.assert_called_once_with(dummy_stream)
        assert mock_embedding_service.get_embedding.call_count == 2

        # Indexing is attempted for both
        assert mock_search_indexer.index_document.call_count == 2
        mock_search_indexer.index_document.assert_has_calls([
            call(chunk1, embedding1),
            call(chunk2, embedding2)
        ])

        # Check that the error for the specific chunk was logged
        mock_logger.error.assert_called_once_with(
            f"Error processing chunk uuid1 for {blob_name}: {test_exception}",
            exc_info=True
        )
        mock_logger.info.assert_any_call(f"Successfully processed and initiated indexing for chunks from {blob_name}")


    def test_process_and_index_pdf_processor_error_propagates(
        self,
        indexing_service,
        mock_pdf_processor,
        mock_embedding_service,
        mock_search_indexer,
        mock_logger
    ):
        dummy_stream = io.BytesIO(b"dummy pdf content")
        blob_name = "processor_error.pdf"
        test_exception = RuntimeError("PDF processing failed badly")

        mock_pdf_processor.process_pdf_to_chunks.side_effect = test_exception

        with pytest.raises(RuntimeError, match="PDF processing failed badly"):
            indexing_service.process_and_index_pdf(dummy_stream, blob_name)

        mock_pdf_processor.process_pdf_to_chunks.assert_called_once_with(dummy_stream)
        mock_embedding_service.get_embedding.assert_not_called()
        mock_search_indexer.index_document.assert_not_called()

        # Check that the overall processing error was logged
        mock_logger.error.assert_called_once_with(
            f"Failed during processing of {blob_name}: {test_exception}",
            exc_info=True
        )
