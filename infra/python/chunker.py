import fitz  # PyMuPDF
from transformers import GPT2TokenizerFast
import uuid
import sys
from openai import AzureOpenAI
import os
import requests
import json


# Settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SHOW_SAMPLE_COUNT = 1  # Number of chunks to display
search_api_url = "https://aifitsearch-generous-raven.search.windows.net/indexes/fitness-rag-index/docs/index?api-version=2023-11-01"
search_api_url = "https://aifitsearch-generous-raven.search.windows.net/indexes/fitness-rag-index/docs/search?api-version=2024-07-01"

search_api_key = "v9F1BtcLwJBXuBgd29u8Q55tbhLi5qWdn7AgkiEOVhAzSeAp8r2z" 
# Load tokenizer
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

deployment_id = "text-embedding-ada-002"

os.environ["AZURE_OPENAI_API_KEY"] = "CkSpIbmVo7x9piXMbjE6TirXqtACC47DRvH0AgaXdwjvBuxTgtvQJQQJ99BDACfhMk5XJ3w3AAAAACOGuMq2" 
client = AzureOpenAI(
    # https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
    api_version="2023-05-15",
    # https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#create-a-resource
    azure_endpoint="https://macie-m976nvww-swedencentral.cognitiveservices.azure.com",
)

def get_embedding(text, model="text-embedding-ada-002"):
    response = client.embeddings.create(
        input=[text],
#        deployment_id=deployment_id,  # This deployment id is created in the Azure portal
        model=model
    )
    return response.data[0].embedding

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text:
            full_text.append((page_num + 1, text.strip()))
    return full_text

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text.strip())
        start += chunk_size - overlap
    return chunks

def process_pdf_to_chunks(pdf_path):
    page_texts = extract_text_from_pdf(pdf_path)
    chunk_records = []

    for page_num, page_text in page_texts:
        chunks = chunk_text(page_text)
        for i, chunk in enumerate(chunks):
            record = {
                "id": str(uuid.uuid4()),
                "content": chunk,
                "metadata": {
                    "source_page": page_num,
                    "chunk_index": i
                }
            }
            chunk_records.append(record)

    return chunk_records

def post_chunk_to_index(chunk):
    chunk['embedding'] = get_embedding(chunk["content"])
    chunk['@search.action'] = "upload"
    if isinstance(chunk.get("metadata"), dict):
    	chunk["metadata"] = json.dumps(chunk["metadata"]) 
    # Prepare the JSON payload
    payload = {"value": [chunk]}
    print(payload)
    # Set the required headers including the API key
    headers = {
        "Content-Type": "application/json",
        "api-key": "v9F1BtcLwJBXuBgd29u8Q55tbhLi5qWdn7AgkiEOVhAzSeAp8r2z" 
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    print("Status Code:", response.status_code)
    print("Response:", response.text)

def search_index(query):
    embedding = get_embedding(query)
    # Headers
    headers = {
        "Content-Type": "application/json",
        "api-key": search_api_key
    }

    # Request body - using the direct REST API format
    body = {
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": "embedding",
                "k": 5
            }
        ],
        "select": "id,content"  # Fields to return
    }

    print(f"Sending request to: {search_api_url}")
    print(f"Request body contains vector with {len(embedding)} dimensions")

    # Make the request
    try:
        response = requests.post(search_api_url, headers=headers, json=body)
        
        # Process the response
        if response.status_code == 200:
            results = response.json()
            print(f"Found {len(results.get('value', []))} results")
            for doc in results.get("value", []):
                print(f"ID: {doc.get('id')}")
                print(f"Content: {doc.get('content', '')}...")
                print("-" * 30)
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
            # Try to parse the error for more details
            try:
                error_details = response.json()
                print("\nDetailed error information:")
                print(json.dumps(error_details, indent=2))
            except:
                pass
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
   pdf_path = sys.argv[1]   # <- change this
   chunks = process_pdf_to_chunks(pdf_path)

   print(f"\n✅ Total chunks generated: {len(chunks)}")
   print(f"\n📄 Showing the first {SHOW_SAMPLE_COUNT} chunks:\n")

   for i, chunk in chunks:#enumerate(chunks[:SHOW_SAMPLE_COUNT]):
       print(f"--- Chunk {i+1} ---")
       print(f"Page: {chunk['metadata']['source_page']}, Chunk Index: {chunk['metadata']['chunk_index']}")
       print(chunk["content"])
       print("\n" + "="*60 + "\n")
       post_chunk_to_index(chunk)
       for chunk in chunks:
        post_chunk_to_index(chunk)
        	
