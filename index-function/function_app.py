import azure.functions as func
import datetime
import json
import logging
import os

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="%UPLOAD_BLOB_PATH%", connection="UPLOAD_STORAGE_CONNECTION_STRING") 
def MyBlobTriggerFunction(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")