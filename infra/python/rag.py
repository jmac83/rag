
from openai import AzureOpenAI
import os
import requests
import json

search_api_url = "https://aifitsearch-generous-raven.search.windows.net/indexes/fitness-rag-index/docs/index?api-version=2023-11-01"
search_api_url = "https://aifitsearch-generous-raven.search.windows.net/indexes/fitness-rag-index/docs/search?api-version=2024-07-01"

search_api_key = "v9F1BtcLwJBXuBgd29u8Q55tbhLi5qWdn7AgkiEOVhAzSeAp8r2z" 
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

def search_index(query, k_top):
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
                "k": k_top
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
            return results.get("value", [])
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

def get_comprehensive_fitness_context():
    """Retrieve a well-rounded set of fitness information from multiple queries"""
    
    # Define a set of generic, useful fitness queries
    queries = [
        "training plans for endurance athletes",
        "effective recovery strategies after intense workouts",
        "nutrition guidelines for athletic performance",
        "injury prevention techniques for runners",
        "heart rate zone training benefits"
    ]
    
    # Collect results from all queries
    all_results = []
    for query in queries:
        print(f"Retrieving information about: {query}")
        results = search_index(query, 2)  # Get top 2 results per query
        all_results.extend(results)
    
    # Format the combined results
    context = "REFERENCE FITNESS INFORMATION:\n\n"
    for i, result in enumerate(all_results, 1):
        content = result.get('content', '')
        # Limit content length to keep it manageable
        if len(content) > 400:  # Shorter excerpts to fit more topics
            content = content[:400] + "..."
        context += f"[{i}] {content}\n\n"
    
    return context


if __name__ == "__main__":
    rag_data = get_comprehensive_fitness_context()
    print(rag_data)