import io
import logging
from .pdfprocessor import PDFProcessor
from .embeddingservice import EmbeddingService
from .azuresearchindexer import AzureSearchIndexer

class PdfIndexingService:
    def __init__(
        self,
        pdf_processor: PDFProcessor,
        embedding_service: EmbeddingService,
        search_indexer: AzureSearchIndexer,
        logger: logging.Logger = logging.getLogger(__name__)
    ):
        self.pdf_processor = pdf_processor
        self.embedding_service = embedding_service
        self.search_indexer = search_indexer
        self.logger = logger

    def process_and_index_pdf(self, pdf_stream: io.BytesIO, blob_name: str):
        self.logger.info(f"Starting processing for PDF: {blob_name}")
        try:
            chunk_records = self.pdf_processor.process_pdf_to_chunks(pdf_stream)
            if not chunk_records:
                self.logger.warning(f"No text chunks were extracted from {blob_name}. Skipping indexing.")
                return

            self.logger.info(f"Extracted {len(chunk_records)} chunks from {blob_name}.")

            for i, chunk in enumerate(chunk_records):
                chunk_id = chunk.get('id', f'chunk_{i}')
                self.logger.debug(f"Processing chunk {i+1}/{len(chunk_records)} (ID: {chunk_id}) for {blob_name}")
                try:
                    embedding = self.embedding_service.get_embedding(chunk['content'])
                    self.logger.debug(f"Generated embedding for chunk {chunk_id}")
                    self.search_indexer.index_document(chunk, embedding)
                    self.logger.debug(f"Indexed chunk {chunk_id}")
                except Exception as chunk_error:
                    self.logger.error(f"Error processing chunk {chunk_id} for {blob_name}: {chunk_error}", exc_info=True)

            self.logger.info(f"Successfully processed and initiated indexing for chunks from {blob_name}")
        except Exception as e:
            self.logger.error(f"Failed during processing of {blob_name}: {e}", exc_info=True)
            raise
