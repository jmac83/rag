
from openai import AzureOpenAI
import os
import requests
import json
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from garmin import simple_fit_to_json
from rag import get_comprehensive_fitness_context
from rag import search_index


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
        context += f"[{i}] {content}\n\n"
    
    return context

if __name__ == "__main__":
    my_garmin_data = simple_fit_to_json('ACTIVITY.FIT')
    rag_data = get_comprehensive_fitness_context()
    print(rag_data)

    endpoint = "https://macie-m976nvww-swedencentral.services.ai.azure.com/models"
    model_name = "DeepSeek-R1"

    client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential("CkSpIbmVo7x9piXMbjE6TirXqtACC47DRvH0AgaXdwjvBuxTgtvQJQQJ99BDACfhMk5XJ3w3AAAAACOGuMq2" ),
    )

    response = client.complete(
        messages=[
            SystemMessage(content="You are an elite fitness and endurance trainer specializing in personalized training plans. Use the reference fitness information provided to create science-based recommendations. Consider the user's Garmin data to tailor your advice to their specific situation."),
            
            # Add RAG data in a system message
            SystemMessage(content=f"""
            Reference fitness information from database:
            {rag_data}
                    """),
                    
            # Add Garmin data and the actual user query in the user message
            UserMessage(content=f"""
            My Garmin fitness data:
            {my_garmin_data}
            I'm 42 yo male, 186cm 90kg. Fairly sporty but endurance is perhaps average.
            Based on my fitness data and your knowledge, please create a training plan for next week that will help me improve my endurance.
                    """)
        ],
    max_tokens=10000,
    model=model_name
)
    print(response.choices[0].message.content)
        	
