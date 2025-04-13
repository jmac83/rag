# rag
graph TD
    A[User] -- 1. Upload File --> B(Azure Blob Storage);
    B -- 2. Triggers --> C{Azure Function (Blob Trigger)};
    C -- 3. Reads File & Chunks --> C; %% Internal processing step
    C -- 4. Request Embedding (for each chunk) --> D[OpenAI Ada API];
    D -- 5. Returns Embedding --> C;
    C -- 6. Publishes (Chunk Text + Embedding) --> E(Azure AI Search Index);

    %% Styling (Optional, but makes it look nicer)
    classDef azure fill:#0078D4,stroke:#005A9E,stroke-width:2px,color:#fff;
    classDef openai fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff;
    class B,C,E azure;
    class D openai;
    class A fill:#f9f,stroke:#333,stroke-width:2px;