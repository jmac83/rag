import azure.functions as func
import datetime
import json
import logging
import os


# --- Logging at Module Load Time (Constructor-like) ---
logging.info("--- function_app.py module loading START ---")
logging.info(f"Python worker initializing at: {datetime.datetime.now()}")

# Example: Log environment variables (be careful not to log secrets!)
blob_path_env = os.environ.get("BLOB_PATH", "Not Set")
storage_conn_env = os.environ.get("STORAGE_CONNECTION_STRING") # Check existence
logging.info(f"BLOB_PATH environment variable: {blob_path_env}")
logging.info(f"STORAGE_CONNECTION_STRING environment variable set: {'Yes' if storage_conn_env else 'No'}")
# --- End of Module Load Logging ---


app = func.FunctionApp()


@app.blob_trigger(arg_name="myblob", path="%BLOB_PATH%", connection="%STORAGE_CONNECTION_STRING%") 
def MyBlobTriggerFunction(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")

@app.route(route="testlog") # Defines the URL path: /api/testlog
def HttpTestFunction(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('--- HTTP Trigger START ---') 
    logging.info('Python HTTP trigger function processed a request.')