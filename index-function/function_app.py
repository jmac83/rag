import azure.functions as func
import logging
import os
import io
from src.pdfprocessor import PDFProcessor
from src.embeddingservice import EmbeddingService
from src.azuresearchindexer import AzureSearchIndexer
from openai import AzureOpenAI
from transformers import GPT2TokenizerFast

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="%UPLOAD_BLOB_PATH%", connection="UPLOAD_STORAGE_CONNECTION_STRING") 
def IndexPdfFunction(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")

    if myblob.name.endswith(".pdf"):
        logging.info(f"Processing PDF blob: {myblob.name}")

        pdf_processor = PDFProcessor(
            GPT2TokenizerFast.from_pretrained("gpt2")
        )

        embedding_service = EmbeddingService(
            AzureOpenAI(
                api_version="2023-05-15",
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
        )
        azure_search_indexer = AzureSearchIndexer(
            search_api_url=os.getenv("AZURE_SEARCH_API_URL"),
            search_api_key=os.getenv("AZURE_SEARCH_API_KEY")
        )

        chunk_records = pdf_processor.process_pdf_to_chunks(io.BytesIO(myblob.read()))
        for chunk in chunk_records:
            logging.info(f"Chunk ID: {chunk['id']}")
            logging.info(f"Chunk Content: {chunk['content'][:50]}...")

            embedding = embedding_service.get_embedding(chunk['content'])
            logging.info(f"Embedding: {embedding[:10]}...")

            logging.info("Posting chunk to Azure Search Indexer")
            azure_search_indexer.index_document(chunk, embedding)
        logging.info(f"Finished processing PDF blob: {myblob.name}")
    else:
        logging.error(f"Blob is not a PDF file: {myblob.name}")