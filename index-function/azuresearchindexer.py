import json
import requests

class AzureSearchIndexer:
    INDEX_NAME = "rag-index"
    API_VERSION = "2023-11-01"
    SEARCH_API_ULR = "{}/indexes/{}/docs/index?api-version={}"

    def __init__(
            self,
            search_api_url: str,
            search_api_key: str
        ):
        self.search_api_url = search_api_url
        self.search_api_key = search_api_key

    def index_document(self, chunk, embedding):
        chunk['embedding'] = embedding
        chunk['@search.action'] = "upload"
        if isinstance(chunk.get("metadata"), dict):
            chunk["metadata"] = json.dumps(chunk["metadata"]) 
        
        payload = {"value": [chunk]}
        print(payload)
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.search_api_key 
        }
        response = requests.post(
            self.SEARCH_API_ULR.format(self.search_api_url, self.INDEX_NAME, self.API_VERSION), 
            headers=headers, 
            data=json.dumps(payload)
        )

        print("Status Code:", response.status_code)
        print("Response:", response.text)