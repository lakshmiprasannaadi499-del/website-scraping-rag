
# Website Scraping RAG Application

## 🏗️ Architecture Explanation
WebRAG Studio follows an end-to-end RAG architecture where website content is collected and converted into a searchable knowledge base.
The website is crawled, cleaned, split into chunks, converted into embeddings, and stored in ChromaDB.
When a user asks a question, the system performs semantic search to retrieve the most relevant chunks.
These chunks are given as context to the Qwen3:8B LLM running through Ollama to generate a grounded answer.
Finally, Streamlit displays the retrieved information and generated answer to the user.

## 🏗️ Architecture

![WebsiteScraping-Architecture](https://github.com/user-attachments/assets/d84bd6b3-0bc3-4591-9e95-6aa0c00c978f)

**WebRAG Studio — End-to-End Project Demo**

https://github.com/user-attachments/assets/b8f6fc74-b405-4d38-b839-9754d570c256

