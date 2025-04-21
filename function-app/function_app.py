import azure.functions as func
import logging
import os
import json
from azure.storage.blob import BlobServiceClient
from src.blobstorageservice import BlobStorageService
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
    UPLOAD_STORAGE_CONNECTION_STRING = os.environ["UPLOAD_STORAGE_CONNECTION_STRING"]
  
    UPLOAD_CONTAINER_NAME = os.environ["UPLOAD_BLOB_PATH"].split("/")[0]
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    openai_client = AzureOpenAI(
        api_version="2023-05-15",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
    indexing_service = PdfIndexingService(
        pdf_processor = PDFProcessor(tokenizer),
        embedding_service = EmbeddingService(openai_client),
        search_indexer = AzureSearchIndexer(
            search_api_url = AZURE_SEARCH_API_URL,
            search_api_key = AZURE_SEARCH_API_KEY
        ),
        logger=logging
    )

    blob_service_client = BlobServiceClient.from_connection_string(UPLOAD_STORAGE_CONNECTION_STRING)
    blob_storage_service = BlobStorageService(blob_service_client) 
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

        indexing_service.process_and_index_pdf(io.BytesIO(myblob.read()), myblob.name)

        logging.info(f"Successfully completed trigger processing for blob: {myblob.name}")
    else:
        logging.error(f"Blob is not a PDF file: {myblob.name}")
        
@app.route(route="blobs", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def list_blobs(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('GET /blobs request received.')
    if not dependencies_initialized:
        return func.HttpResponse(json.dumps({"error":"Service not ready"}), status_code=503, mimetype="application/json")

    prefix = req.params.get('prefix')

    try:
        blob_data = blob_storage_service.list_blob_names(UPLOAD_CONTAINER_NAME, prefix)
        return func.HttpResponse(json.dumps(blob_data), mimetype="application/json")
    except Exception as e:
        logging.error(f"Error listing blobs: {e}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "Failed to list blobs"}), status_code=500, mimetype="application/json")

@app.route(route="blobs", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def upload_blob(req: func.HttpRequest) -> func.HttpResponse:
    if not dependencies_initialized:
        return func.HttpResponse(json.dumps({"error":"Service not ready"}), status_code=503, mimetype="application/json")

    # Get blob path from header instead of route parameter
    blob_path = req.headers.get("x-blob-path")
    if not blob_path:
         return func.HttpResponse(json.dumps({"error": "Blob path missing in headers"}), status_code=400, mimetype="application/json")

    try:
        file_content = req.get_body()
        if not file_content:
             return func.HttpResponse(json.dumps({"error": "Request body is empty"}), status_code=400, mimetype="application/json")

        upload_result = blob_storage_service.upload_blob(
            container_name=UPLOAD_CONTAINER_NAME,
            blob_name=blob_path,
            file_content=file_content,
            overwrite=True 
        )

        status_code = 201 if upload_result.get("success") else 500
        return func.HttpResponse(json.dumps(upload_result), status_code=status_code, mimetype="application/json")

    except Exception as e:
        logging.error(f"Upload Error ({UPLOAD_CONTAINER_NAME}/{blob_path}): {e}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "An unexpected error occurred"}), status_code=500, mimetype="application/json")
