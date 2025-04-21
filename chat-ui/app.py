import streamlit as st
import os
import logging
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import json
import requests # Added
import pandas as pd # Added

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
AZURE_SEARCH_API_URL = os.environ.get("AZURE_SEARCH_API_URL")
AZURE_SEARCH_API_KEY = os.environ.get("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = "rag-index"

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-4o-chat"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-ada-002"

AZURE_FUNCTION_APP_URL = os.environ.get("AZURE_FUNCTION_APP_URL")
AZURE_FUNCTION_APP_KEY = os.environ.get("AZURE_FUNCTION_APP_KEY")

# --- Client Initialization ---
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

# --- RAG Core Functions ---
# (Keep get_embedding, search_documents, get_chat_completion functions as they were)
def get_embedding(text: str):
    if not all([openai_client, AZURE_OPENAI_EMBEDDING_DEPLOYMENT]):
        st.error("OpenAI Embedding client not configured.")
        return None
    try:
        return openai_client.embeddings.create(input=[text], model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT).data[0].embedding
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
        if not vector: return []
        vector_query = {"vector": [float(x) for x in vector], "k": top_k, "fields": "embedding", "kind": "vector"}
        results = search_client.search(search_text=None, vector_queries=[vector_query], select=["id", "content", "metadata"])
        return list(results)
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        st.error(f"Azure Search query failed: {e}")
        return []

def get_chat_completion(user_query: str, retrieved_docs: list):
    if not all([openai_client, AZURE_OPENAI_CHAT_DEPLOYMENT]):
        st.error("OpenAI Chat client not configured.")
        return "Error: Chat client not configured."

    system_message = "Answer the user's query using *only* the provided context documents. If the context doesn't contain the answer, state that.\n\nContext Documents:\n---\n"
    context = "\n---\n".join([
        f"Source Page: {json.loads(doc['metadata']).get('source_page', 'N/A') if isinstance(doc['metadata'], str) else doc.get('metadata', {}).get('source_page', 'N/A')}\nContent: {doc['content']}"
        for doc in retrieved_docs
    ]) if retrieved_docs else "No relevant documents found."

    messages = [{"role": "system", "content": system_message + context}, {"role": "user", "content": user_query}]
    try:
        response = openai_client.chat.completions.create(model=AZURE_OPENAI_CHAT_DEPLOYMENT, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting chat completion: {e}")
        st.error(f"Azure OpenAI call failed: {e}")
        return f"Error generating response: {e}"

# --- Blob Storage Interaction Functions ---
def get_function_headers():
    headers = {"Content-Type": "application/json"}
    if AZURE_FUNCTION_APP_KEY: headers["x-functions-key"] = AZURE_FUNCTION_APP_KEY
    return headers

def fetch_blobs_from_function():
    if not AZURE_FUNCTION_APP_URL:
        st.sidebar.error("Function App URL missing.")
        return []
    list_url = f"{AZURE_FUNCTION_APP_URL}/api/blobs"
    try:
        response = requests.get(list_url, headers=get_function_headers(), timeout=15)
        response.raise_for_status()
        data = response.json()
        if 'blobs' in data and isinstance(data['blobs'], list):
            return sorted([blob.get('name', 'Unknown Name') for blob in data['blobs']], key=os.path.basename)
        else:
            st.sidebar.warning("API response format incorrect.", icon="⚠️")
            return []
    except (requests.exceptions.RequestException, json.JSONDecodeError, Exception) as e:
        logger.error(f"Error fetching blobs: {e}")
        st.sidebar.error(f"Error fetching list: {e}", icon="🚨")
        return []

def upload_blob_to_function(file_bytes, filename):
    if not AZURE_FUNCTION_APP_URL:
        st.sidebar.error("Function App URL missing.")
        return False
    if not filename or not file_bytes:
        st.sidebar.warning("File and filename required.", icon="⚠️")
        return False

    upload_url = f"{AZURE_FUNCTION_APP_URL}/api/blobs"
    headers = get_function_headers()
    headers['Content-Type'] = 'application/octet-stream'
    headers['x-blob-path'] = filename
    try:
        # *** Use shorter spinner text ***
        with st.spinner("Uploading..."):
            response = requests.post(upload_url, headers=headers, data=file_bytes, timeout=60)
            response.raise_for_status()
        # Use success message within the sidebar
        st.sidebar.success(f"Uploaded '{filename}'!", icon="✅")
        return True
    except requests.exceptions.RequestException as e:
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try: error_detail = e.response.json().get('error', e.response.text)
             except json.JSONDecodeError: error_detail = e.response.text
        logger.error(f"Upload error: {error_detail}")
        st.sidebar.error(f"Upload Error: {error_detail}", icon="🚨")
        return False
    except Exception as e:
        logger.error(f"Unexpected upload error: {e}")
        st.sidebar.error(f"Upload Error: {e}", icon="🚨")
        return False


# --- Streamlit App UI ---

# --- Sidebar Document Management (Minimalist v4) ---
with st.sidebar:
    if not AZURE_FUNCTION_APP_URL:
        st.warning("Function App URL missing.", icon="⚠️")
    else:
        # --- Display List First ---
        col_header, col_refresh = st.columns([0.85, 0.15], gap="small")
        with col_header:
            st.subheader("Indexed Documents")
        with col_refresh:
            refresh_button = st.button("🔄", key="sidebar_refresh_button", help="Refresh list")

        list_placeholder = st.container()

        def display_simple_blob_list(max_len=25):
            blob_names = fetch_blobs_from_function()
            list_placeholder.empty()
            with list_placeholder:
                if blob_names:
                    st.markdown("""<style> .indexed-doc-item { font-size: 0.9em; padding-bottom: 2px; } </style>""", unsafe_allow_html=True)
                    for full_blob_name in blob_names:
                        base_name = os.path.basename(full_blob_name)
                        display_name = (base_name[:max_len-3] + "...") if len(base_name) > max_len else base_name
                        tooltip_html = f"""
                        <div class="indexed-doc-item" title="{full_blob_name}" style="cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            📄 {display_name}
                        </div>
                        """
                        st.markdown(tooltip_html, unsafe_allow_html=True)
                else:
                    st.info("No documents indexed.")

        # Refresh logic
        if refresh_button:
             if 'blob_list_loaded' in st.session_state: del st.session_state['blob_list_loaded']
             display_simple_blob_list()
             st.session_state.blob_list_loaded = True
        elif 'blob_list_loaded' not in st.session_state:
             display_simple_blob_list()
             st.session_state.blob_list_loaded = True
        else:
             display_simple_blob_list()

        # --- Upload Section Below ---
        st.subheader("Upload New")

        # *** Removed columns for upload section ***
        uploaded_file = st.file_uploader(
            "Select file",
            type=None,
            key="sidebar_file_uploader",
            label_visibility="collapsed"
            # Cannot easily hide internal "Drag and drop..." text
        )

        # *** Upload button appears *below* uploader when file is selected ***
        if uploaded_file is not None:
            if st.button(f"⬆️ Upload", key="sidebar_upload_button", help=f"Upload {uploaded_file.name}"):
                success = upload_blob_to_function(uploaded_file.getvalue(), uploaded_file.name)
                if success:
                    if 'blob_list_loaded' in st.session_state: del st.session_state['blob_list_loaded']
                    st.rerun()


# --- Main Chat Interface ---
st.title("📚 RAG Chat Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question"):
    if not all([search_client, openai_client, AZURE_OPENAI_CHAT_DEPLOYMENT]):
         st.error("Application is not fully configured.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            retrieved_docs = search_documents(prompt)
            response = get_chat_completion(prompt, retrieved_docs)

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)