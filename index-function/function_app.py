import azure.functions as func
import datetime
import json
import logging
import os
import io
from pdfprocessor import PDFProcessor
from embeddingservice import EmbeddingService
from openai import AzureOpenAI

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="%UPLOAD_BLOB_PATH%", connection="UPLOAD_STORAGE_CONNECTION_STRING") 
def IndexPdfFunction(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")

    if myblob.name.endswith(".pdf"):
        logging.info(f"Processing PDF blob: {myblob.name}")

        pdf_processor = PDFProcessor()
        
        openai_client = AzureOpenAI(
            api_version="2023-05-15",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        embedding_service = EmbeddingService(openai_client)
                
        chunk_records = pdf_processor.process_pdf_to_chunks(io.BytesIO(myblob.read()))
        for chunk in chunk_records:
            logging.info(f"Chunk ID: {chunk['id']}")
            logging.info(f"Chunk Content: {chunk['content'][:50]}...")

            embedding = embedding_service.get_embedding(chunk['content'])
            logging.info(f"Chunk Metadata: {embedding}")
    else:
        logging.error(f"Blob is not a PDF file: {myblob.name}")