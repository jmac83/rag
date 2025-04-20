import azure.functions as func
import logging
import os
import io
from src.pdfprocessor import PDFProcessor
from src.embeddingservice import EmbeddingService
from src.azuresearchindexer import AzureSearchIndexer
from src.pdfindexingservice import PdfIndexingService
from openai import AzureOpenAI
from transformers import GPT2TokenizerFast

app = func.FunctionApp()

try:
    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
    AZURE_SEARCH_API_URL = os.environ["AZURE_SEARCH_API_URL"]
    AZURE_SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    openai_client = AzureOpenAI(
        api_version="2023-05-15",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
    dependencies_initialized = True
    logging.info("Core dependencies initialized successfully.")
except Exception as e:
    logging.critical(f"Failed to initialize core dependencies: {e}", exc_info=True)
    dependencies_initialized = False


@app.blob_trigger(arg_name="myblob", path="%UPLOAD_BLOB_PATH%", connection="UPLOAD_STORAGE_CONNECTION_STRING") 
def IndexPdfFunction(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")

    if myblob.name.endswith(".pdf"):

        indexing_service = PdfIndexingService(
            pdf_processor = PDFProcessor(tokenizer),
            embedding_service = EmbeddingService(openai_client),
            search_indexer = AzureSearchIndexer(
                search_api_url = AZURE_SEARCH_API_URL,
                search_api_key = AZURE_SEARCH_API_KEY
            ),
            logger=logging
        )

        pdf_content_stream = io.BytesIO(myblob.read())

        indexing_service.process_and_index_pdf(pdf_content_stream, myblob.name)

        logging.info(f"Successfully completed trigger processing for blob: {myblob.name}")
    else:
        logging.error(f"Blob is not a PDF file: {myblob.name}")