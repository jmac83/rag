import io
import uuid
from unittest.mock import MagicMock, patch, call, PropertyMock
import pytest
from transformers import GPT2TokenizerFast
from src.pdfprocessor import PDFProcessor

# --- Fixtures ---

@pytest.fixture
def mock_tokenizer():
    # Create a mock that mimics the tokenizer interface
    mock = MagicMock(spec=GPT2TokenizerFast)
    mock.encode.side_effect = lambda text: list(range(len(text)))
    mock.decode.side_effect = lambda tokens: "".join([f"t{t}" for t in tokens])
    return mock

# --- Test Class ---

class TestPDFProcessor:

    def test_init(self, mock_tokenizer):
        processor = PDFProcessor(tokenizer=mock_tokenizer)
        assert processor.tokenizer is mock_tokenizer

    # Test the static-like method __extract_text_from_pdf
    @patch('src.pdfprocessor.fitz.open') # Patch where fitz is imported/used
    def test_extract_text_from_pdf_logic(self, mock_fitz_open):
        # Arrange
        # Mock the document object returned by fitz.open
        mock_doc = MagicMock()

        # Mock page objects
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = " Text from page 1. \n"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Text from page 2."
        mock_page3 = MagicMock()
        mock_page3.get_text.return_value = "" # Empty text page
        mock_page4 = MagicMock()
        mock_page4.get_text.return_value = None # None text page

        # Make the mock document iterable, yielding the mock pages
        mock_doc.__iter__.return_value = [mock_page1, mock_page2, mock_page3, mock_page4]
        mock_fitz_open.return_value = mock_doc # fitz.open returns our mock doc

        dummy_bytes = b"dummy pdf bytes"
        pdf_stream = io.BytesIO(dummy_bytes)

        extracted_data = PDFProcessor._PDFProcessor__extract_text_from_pdf(self, pdf_stream)

        # Assert
        mock_fitz_open.assert_called_once_with(stream=dummy_bytes, filetype="pdf")
        assert mock_page1.get_text.call_count == 1
        assert mock_page2.get_text.call_count == 1
        assert mock_page3.get_text.call_count == 1
        assert mock_page4.get_text.call_count == 1

        assert extracted_data == [
            (1, "Text from page 1."), # Page num, stripped text
            (2, "Text from page 2."),
            # Page 3 & 4 skipped as text is empty or None
        ]

    def test_chunk_text_logic(self, mock_tokenizer):
        # Arrange
        processor = PDFProcessor(tokenizer=mock_tokenizer)
        processor.CHUNK_SIZE = 5
        processor.CHUNK_OVERLAP = 1

        test_text = "abcdefghij" # encode -> [0,1,2,3,4,5,6,7,8,9]

        # Act
        chunks = processor._PDFProcessor__chunk_text(test_text)

        # Assert
        # Expected behavior with size=5, overlap=1:
        # 1. Tokens [0, 1, 2, 3, 4] -> decode -> "t0t1t2t3t4"
        # 2. Start next at 0 + 5 - 1 = 4. Tokens [4, 5, 6, 7, 8] -> decode -> "t4t5t6t7t8"
        # 3. Start next at 4 + 5 - 1 = 8. Tokens [8, 9] -> decode -> "t8t9"
        assert chunks == ["t0t1t2t3t4", "t4t5t6t7t8", "t8t9"]
        mock_tokenizer.encode.assert_called_once_with(test_text)
        assert mock_tokenizer.decode.call_count == 3
        mock_tokenizer.decode.assert_has_calls([
            call([0, 1, 2, 3, 4]),
            call([4, 5, 6, 7, 8]),
            call([8, 9])
        ])

    # Test the public orchestration method
    @patch('src.pdfprocessor.uuid.uuid4')
    @patch.object(PDFProcessor, '_PDFProcessor__chunk_text')
    @patch.object(PDFProcessor, '_PDFProcessor__extract_text_from_pdf')
    def test_process_pdf_to_chunks_orchestration(
        self, mock_extract, mock_chunk, mock_uuid, mock_tokenizer
    ):
        # Arrange
        processor = PDFProcessor(tokenizer=mock_tokenizer)
        dummy_stream = io.BytesIO(b"dummy pdf")

        # Configure mocks for internal methods
        mock_extract.return_value = [
            (1, "Full text page 1."),
            (3, "Full text page 3.") # Simulate skipping page 2
        ]

        # Make mock_chunk return different values based on input page text
        def chunk_side_effect(text):
            if text == "Full text page 1.":
                return ["chunk1a", "chunk1b"]
            elif text == "Full text page 3.":
                return ["chunk3a"]
            else:
                return []
        mock_chunk.side_effect = chunk_side_effect

        # Configure mock UUIDs
        mock_uuid_values = [uuid.UUID('11111111-1111-1111-1111-111111111111'),
                            uuid.UUID('22222222-2222-2222-2222-222222222222'),
                            uuid.UUID('33333333-3333-3333-3333-333333333333')]
        mock_uuid.side_effect = [str(u) for u in mock_uuid_values]

        # Act
        chunk_records = processor.process_pdf_to_chunks(dummy_stream)

        # Assert
        # Check internal methods were called correctly
        mock_extract.assert_called_once_with(dummy_stream)
        assert mock_chunk.call_count == 2
        mock_chunk.assert_has_calls([
            call("Full text page 1."),
            call("Full text page 3.")
        ], any_order=False) # Order matters here

        # Check uuid was called for each final chunk
        assert mock_uuid.call_count == 3

        # Check the final output structure
        expected_records = [
            {
                "id": '11111111-1111-1111-1111-111111111111',
                "content": "chunk1a",
                "metadata": {"source_page": 1, "chunk_index": 0}
            },
            {
                "id": '22222222-2222-2222-2222-222222222222',
                "content": "chunk1b",
                "metadata": {"source_page": 1, "chunk_index": 1}
            },
            {
                "id": '33333333-3333-3333-3333-333333333333',
                "content": "chunk3a",
                "metadata": {"source_page": 3, "chunk_index": 0}
            }
        ]
        assert chunk_records == expected_records

