# chat-ui/app.py
import streamlit as st
import os
import logging
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AZURE_SEARCH_API_URL = os.environ.get("AZURE_SEARCH_API_URL")
AZURE_SEARCH_API_KEY = os.environ.get("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = "rag-index"

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-4o-chat"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-ada-002"

search_credential = AzureKeyCredential(AZURE_SEARCH_API_KEY) if AZURE_SEARCH_API_KEY else None
search_client = SearchClient(endpoint=AZURE_SEARCH_API_URL,
                             index_name=AZURE_SEARCH_INDEX_NAME,
                             credential=search_credential,
                             api_version="2023-11-01") if AZURE_SEARCH_API_URL and search_credential else None

openai_client = AzureOpenAI(
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
) if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY else None


def get_embedding(text: str):
    if not openai_client or not AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
        st.error("OpenAI Embedding client not configured.")
        return None
    try:
        return openai_client.embeddings.create(
            input=[text], model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        ).data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        st.error(f"Failed to generate embedding: {e}")
        return None

def search_documents(query_text: str, top_k: int = 3):
    if not search_client:
        st.error("Azure Search client not configured.")
        return []
    try:
        vector = get_embedding(query_text)
        print(vector)
        if not vector:
            return []
        
        vector_as_list = [float(x) for x in vector]
        
        vector_query = {
            "vector": vector_as_list,
            "k": top_k,
            "fields": "embedding",
            "kind": "vector"
        }
        results = search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=["id", "content", "metadata"],
        )
        return list(results)
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        st.error(f"Azure Search query failed: {e}")
        return []

def get_chat_completion(user_query: str, retrieved_docs: list):
    if not openai_client or not AZURE_OPENAI_CHAT_DEPLOYMENT:
        st.error("OpenAI Chat client not configured.")
        return "Error: Chat client not configured."
    print(100*"-")
    print(retrieved_docs)
    print(100*"-")
    system_message = """You are an AI assistant helping answer questions based on the provided context documents.
Answer the user's query using *only* the information found in the context documents below.
If the context doesn't contain the answer, state that you cannot answer based on the provided information.
Be concise and helpful. Cite the source page from the metadata if available.

Context Documents:
---
"""
    context = "\n---\n".join([
        f"Source Page: {json.loads(doc['metadata']).get('source_page', 'N/A') if isinstance(doc['metadata'], str) else doc.get('metadata', {}).get('source_page', 'N/A')}\nContent: {doc['content']}" 
        for doc in retrieved_docs
    ])
    if not retrieved_docs:
        context = "No relevant documents found."

    messages = [
        {"role": "system", "content": system_message + context},
        {"role": "user", "content": user_query}
    ]

    try:
        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting chat completion: {e}")
        st.error(f"Azure OpenAI call failed: {e}")
        return f"Error generating response: {e}"


st.title("📚 RAG Chat Assistant")
st.caption("Ask questions about your indexed documents.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is your question?"):
    if not all([search_client, openai_client, AZURE_OPENAI_CHAT_DEPLOYMENT]):
         st.error("Application is not fully configured. Please check environment variables.")
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Searching documents and thinking..."):
            retrieved_docs = search_documents(prompt)
            response = get_chat_completion(prompt, retrieved_docs)

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

